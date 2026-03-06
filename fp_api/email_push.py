import threading
import asyncio
import os
import re
import uuid
import imaplib
import email as pyemail
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx

from config import config
from database import DatabaseManager


_email_jobs: Dict[str, Dict[str, Any]] = {}
_email_jobs_lock = threading.Lock()


def _safe_decode_header(raw: Union[str, bytes]) -> str:
    if not raw:
        return ""
    # If raw is bytes, decode it first
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8", errors="ignore")
        except Exception:
            raw = str(raw)
    try:
        parts = decode_header(raw)
        out: List[str] = []
        for content, enc in parts:
            if isinstance(content, bytes):
                try:
                    out.append(content.decode(enc or "utf-8", errors="ignore"))
                except Exception:
                    out.append(content.decode("utf-8", errors="ignore"))
            else:
                out.append(str(content))
        return "".join(out)
    except Exception:
        return str(raw)


def _imap_host_for_email(addr: str) -> str:
    # 默认按 QQ 邮箱
    domain = (addr.split("@", 1)[-1] or "").lower()
    if domain in {"qq.com", "foxmail.com"}:
        return "imap.qq.com"
    if domain == "163.com":
        return "imap.163.com"
    if domain == "126.com":
        return "imap.126.com"
    if domain == "gmail.com":
        return "imap.gmail.com"
    # fallback
    return f"imap.{domain}" if domain else "imap.qq.com"


def _extract_links_from_html(html: str) -> List[str]:
    if not html:
        return []
    # 提取 href 链接
    links = re.findall(r'href=[\"\']?(https?://[^\"\'\s>]+)', html, flags=re.I)
    # 仅保留可能是发票下载/平台链接
    keep: List[str] = []
    for u in links:
        if any(k in u.lower() for k in ["jss.com.cn", "nnfp", "fapiao.com", "invoice", "download", "/pdf", ".pdf"]):
            keep.append(u)
    # 去重
    seen = set()
    out = []
    for u in keep:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


async def _download_link_best_effort(url: str, save_dir: str) -> Optional[str]:
    """尽力从链接下载文件。

    说明：部分平台（如诺诺）可能需要 JS 才能触发下载；这种情况这里会失败并返回 None。
    """
    os.makedirs(save_dir, exist_ok=True)
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return None

            ctype = (r.headers.get("content-type") or "").lower()
            if not any(x in ctype for x in ["pdf", "image", "octet-stream", "application"]):
                return None

            cd = r.headers.get("content-disposition") or ""
            filename = None
            m = re.search(r"filename\*=UTF-8''([^;]+)", cd)
            if m:
                filename = m.group(1)
            if not filename:
                m = re.search(r'filename="?([^";]+)"?', cd)
                if m:
                    filename = m.group(1)

            if not filename:
                # 兜底：从 URL 取
                filename = url.split("?")[0].rsplit("/", 1)[-1] or f"link_{uuid.uuid4().hex}"

            filename = _safe_filename(filename)
            if not os.path.splitext(filename)[1]:
                if "pdf" in ctype:
                    filename += ".pdf"
                elif "png" in ctype:
                    filename += ".png"
                elif "jpeg" in ctype or "jpg" in ctype:
                    filename += ".jpg"

            path = os.path.join(save_dir, filename)
            with open(path, "wb") as f:
                f.write(r.content)
            return path
    except Exception:
        return None


def _safe_filename(name: str) -> str:
    name = name.strip().replace("\\", "_").replace("/", "_")
    name = re.sub(r"\s+", " ", name)
    return name or f"file_{uuid.uuid4().hex}"


def _group_choose_files(files: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """附件选择策略。

    入参：[(filename, abs_path), ...]
    出参：过滤后的文件列表（每组只保留一个），优先图片格式。
    """

    def key_base(fn: str) -> str:
        b = os.path.basename(fn)
        b = re.sub(r"\.(pdf|ofd|xml|jpg|jpeg|png|webp)$", "", b, flags=re.I)
        return b

    priority = {".jpg": 1, ".jpeg": 1, ".png": 1, ".webp": 1, ".pdf": 2, ".ofd": 3, ".xml": 4}

    grouped: Dict[str, List[Tuple[str, str]]] = {}
    for fn, p in files:
        grouped.setdefault(key_base(fn), []).append((fn, p))

    chosen: List[Tuple[str, str]] = []
    for _, items in grouped.items():
        items_sorted = sorted(
            items,
            key=lambda it: priority.get(os.path.splitext(it[0].lower())[1], 99),
        )
        chosen.append(items_sorted[0])

    return chosen


def start_email_push_job(user_id: str, mailbox: str, auth_code: str, days: int) -> str:
    job_id = uuid.uuid4().hex
    with _email_jobs_lock:
        _email_jobs[job_id] = {
            "status": "queued",
            "user_id": user_id,
            "mailbox": mailbox,
            "days": days,
            "total_messages": 0,
            "matched_messages": 0,
            "downloaded": 0,
            "imported": 0,
            "failed": 0,
            "logs": [],
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
        }

    t = threading.Thread(
        target=_run_email_push_job_sync,
        args=(job_id, user_id, mailbox, auth_code, days),
        daemon=True,
    )
    t.start()
    return job_id


def get_email_push_job(job_id: str) -> Dict[str, Any]:
    with _email_jobs_lock:
        j = _email_jobs.get(job_id)
        if not j:
            return {"status": "not_found"}
        # 返回浅拷贝，避免外部修改内部状态
        return dict(j)


def _log(job_id: str, msg: str):
    with _email_jobs_lock:
        j = _email_jobs.get(job_id)
        if not j:
            return
        logs: list = j.get("logs") or []
        logs.append(f"{datetime.now().strftime('%H:%M:%S')} {msg}")
        j["logs"] = logs[-200:]


def _set(job_id: str, **kwargs):
    with _email_jobs_lock:
        if job_id in _email_jobs:
            _email_jobs[job_id].update(kwargs)


def _run_email_push_job_sync(job_id: str, user_id: str, mailbox: str, auth_code: str, days: int):
    from services import file_service  # 避免循环 import

    _set(job_id, status="running")
    _log(job_id, "开始拉取邮箱邮件...")

    db = DatabaseManager()
    user = db.get_user_by_id(user_id)
    if not user:
        _set(job_id, status="error", finished_at=datetime.now().isoformat())
        _log(job_id, "用户不存在")
        return

    host = _imap_host_for_email(mailbox)
    start_date = (datetime.now() - timedelta(days=days)).date()
    today = datetime.now().date()

    save_dir = os.path.join(config.get_upload_dir(user_id), "_email_tmp", job_id)
    os.makedirs(save_dir, exist_ok=True)

    matched_ids: List[bytes] = []

    try:
        imap = imaplib.IMAP4_SSL(host)
        # imaplib 在 Python3 中期望的是 str，这里不要手动 encode
        imap.login(mailbox, auth_code)
        imap.select("INBOX")

        status, data = imap.search(None, "ALL")
        if status != "OK":
            raise RuntimeError("IMAP 搜索失败")

        all_ids = data[0].split()
        _set(job_id, total_messages=len(all_ids))
        _log(job_id, f"邮箱总邮件数: {len(all_ids)}")

        # 先筛选（仅拉取头部，降低流量）
        for mid in all_ids:
            try:
                _, head = imap.fetch(mid, "(BODY[HEADER.FIELDS (SUBJECT DATE)])")
                if not head or not head[0] or not head[0][1]:
                    continue

                msg = pyemail.message_from_bytes(head[0][1])
                subject = _safe_decode_header(msg.get("Subject", ""))
                if "发票" not in subject:
                    continue

                date_str = msg.get("Date", "")
                try:
                    msg_dt = parsedate_to_datetime(date_str)
                    if msg_dt.tzinfo is not None:
                        msg_dt = msg_dt.astimezone().replace(tzinfo=None)
                    msg_date = msg_dt.date()
                except Exception:
                    continue

                if not (start_date <= msg_date <= today):
                    continue

                matched_ids.append(mid)
            except Exception:
                continue

        _set(job_id, matched_messages=len(matched_ids))
        _log(job_id, f"命中发票主题邮件: {len(matched_ids)}")

        if not matched_ids:
            _set(job_id, status="completed", finished_at=datetime.now().isoformat())
            _log(job_id, "未找到符合条件的发票邮件")
            imap.logout()
            return

        # 逐封处理
        for idx, mid in enumerate(matched_ids, start=1):
            _log(job_id, f"处理邮件 {idx}/{len(matched_ids)}")
            try:
                _, mdata = imap.fetch(mid, "(RFC822)")
                if not mdata or not mdata[0] or not mdata[0][1]:
                    continue
                msg = pyemail.message_from_bytes(mdata[0][1])

                attachments: List[Tuple[str, str]] = []
                links: List[str] = []

                for part in msg.walk():
                    filename = part.get_filename()
                    content_type = part.get_content_type()

                    if filename:
                        fname = _safe_decode_header(filename)
                        ext = os.path.splitext(fname.lower())[1]
                        if ext in {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".ofd", ".xml"}:
                            local_name = _safe_filename(f"{mid.decode(errors='ignore')}_{fname}")
                            local_path = os.path.join(save_dir, local_name)
                            payload = part.get_payload(decode=True)
                            if payload:
                                with open(local_path, "wb") as f:
                                    f.write(payload)
                                attachments.append((fname, local_path))
                    elif content_type == "text/html":
                        try:
                            charset = part.get_content_charset() or "utf-8"
                            html = part.get_payload(decode=True)
                            if isinstance(html, (bytes, bytearray)):
                                html = html.decode(charset, errors="ignore")
                            else:
                                html = str(html)
                            links.extend(_extract_links_from_html(html))
                        except Exception:
                            pass

                chosen = _group_choose_files(attachments)

                # 链接尝试下载（优先用于诺诺等）
                for link in links:
                    # 诺诺发票：优先尝试
                    if any(k in link.lower() for k in ["jss.com.cn", "nnfp"]):
                        p = _download_link_best_effort_sync(link, save_dir)
                        if p:
                            chosen.append((os.path.basename(p), p))
                        else:
                            _log(job_id, f"诺诺链接无法直接下载（可能需要浏览器自动化）: {link}")

                if not chosen:
                    continue

                with _email_jobs_lock:
                    current_downloaded = (_email_jobs.get(job_id) or {}).get("downloaded", 0)
                _set(job_id, downloaded=current_downloaded + len(chosen))

                # 导入：复用 upload 的预处理入库逻辑
                for original_name, local_path in chosen:
                    try:
                        asyncio_run(file_service.import_local_file(user_id=user_id, src_path=local_path, original_filename=original_name))
                        with _email_jobs_lock:
                            current_imported = (_email_jobs.get(job_id) or {}).get("imported", 0)
                        _set(job_id, imported=current_imported + 1)
                    except Exception as e:
                        with _email_jobs_lock:
                            current_failed = (_email_jobs.get(job_id) or {}).get("failed", 0)
                        _set(job_id, failed=current_failed + 1)
                        _log(job_id, f"入库失败: {original_name}: {str(e)}")

            except Exception as e:
                with _email_jobs_lock:
                    current_failed = (_email_jobs.get(job_id) or {}).get("failed", 0)
                _set(job_id, failed=current_failed + 1)
                _log(job_id, f"邮件处理失败: {str(e)}")

        imap.logout()
        _set(job_id, status="completed", finished_at=datetime.now().isoformat())
        _log(job_id, "邮箱推送完成")

    except Exception as e:
        _set(job_id, status="error", finished_at=datetime.now().isoformat())
        _log(job_id, f"任务失败: {str(e)}")


def asyncio_run(coro):
    """在后台线程中运行 async 协程。"""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        # 已存在事件循环时兜底
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


def _download_link_best_effort_sync(url: str, save_dir: str) -> Optional[str]:
    """同步版链接下载（用于后台线程）。"""
    os.makedirs(save_dir, exist_ok=True)
    try:
        with httpx.Client(follow_redirects=True, timeout=30.0) as client:
            r = client.get(url)
            if r.status_code != 200:
                return None

            ctype = (r.headers.get("content-type") or "").lower()
            if not any(x in ctype for x in ["pdf", "image", "octet-stream", "application"]):
                return None

            cd = r.headers.get("content-disposition") or ""
            filename = None
            m = re.search(r"filename\*=UTF-8''([^;]+)", cd)
            if m:
                filename = m.group(1)
            if not filename:
                m = re.search(r'filename="?([^";]+)"?', cd)
                if m:
                    filename = m.group(1)

            if not filename:
                filename = url.split("?")[0].rsplit("/", 1)[-1] or f"link_{uuid.uuid4().hex}"

            filename = _safe_filename(filename)
            if not os.path.splitext(filename)[1]:
                if "pdf" in ctype:
                    filename += ".pdf"
                elif "png" in ctype:
                    filename += ".png"
                elif "jpeg" in ctype or "jpg" in ctype:
                    filename += ".jpg"

            path = os.path.join(save_dir, filename)
            with open(path, "wb") as f:
                f.write(r.content)
            return path
    except Exception:
        return None
