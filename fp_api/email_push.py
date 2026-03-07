import asyncio
import imaplib
import os
import re
import shutil
import threading
import uuid
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import email as pyemail
import httpx

from config import config
from database import DatabaseManager


_email_jobs: Dict[str, Dict[str, Any]] = {}
_email_jobs_lock = threading.Lock()

_EMAIL_TERMINAL_STATUS = {"completed", "failed", "partial_success", "cancelled"}
_EMAIL_STAGE_BASE_PROGRESS = {
    "queued": 0.0,
    "connect_imap": 8.0,
    "select_mailbox": 15.0,
    "search_emails": 25.0,
    "filter_emails": 35.0,
    "parse_message": 48.0,
    "download_attachment": 62.0,
    "import_invoice": 75.0,
    "trigger_recognition": 88.0,
    "finalize": 96.0,
}


def _email_now() -> str:
    return datetime.now().isoformat()


def _safe_filename(name: str) -> str:
    name = name.strip().replace("\\", "_").replace("/", "_")
    name = re.sub(r"\s+", " ", name)
    return name or f"file_{uuid.uuid4().hex}"


def _safe_decode_header(raw: Union[str, bytes]) -> str:
    if not raw:
        return ""
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
    domain = (addr.split("@", 1)[-1] or "").lower()
    if domain in {"qq.com", "foxmail.com"}:
        return "imap.qq.com"
    if domain == "163.com":
        return "imap.163.com"
    if domain == "126.com":
        return "imap.126.com"
    if domain == "gmail.com":
        return "imap.gmail.com"
    return f"imap.{domain}" if domain else "imap.qq.com"


def _extract_links_from_html(html: str) -> List[str]:
    if not html:
        return []
    links = re.findall(r'href=[\"\']?(https?://[^\"\'\s>]+)', html, flags=re.I)
    keep: List[str] = []
    for u in links:
        if any(k in u.lower() for k in ["jss.com.cn", "nnfp", "fapiao.com", "invoice", "download", "/pdf", ".pdf"]):
            keep.append(u)
    out: List[str] = []
    seen = set()
    for u in keep:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def _group_choose_files(files: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    # 输入: [(filename, abs_path), ...]
    # 输出: 同名主文件只保留优先级最高的一个
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
        items_sorted = sorted(items, key=lambda it: priority.get(os.path.splitext(it[0].lower())[1], 99))
        chosen.append(items_sorted[0])
    return chosen


def _download_link_best_effort_sync(url: str, save_dir: str) -> Optional[str]:
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


def asyncio_run(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


def _calc_progress(job: Dict[str, Any]) -> float:
    status = (job.get("status") or "queued").lower()
    if status in _EMAIL_TERMINAL_STATUS:
        return 100.0

    stage = job.get("current_stage") or "queued"
    base = float(_EMAIL_STAGE_BASE_PROGRESS.get(stage, 0.0))

    matched = int(job.get("matched_emails") or 0)
    imported = int(job.get("imported_invoices") or 0)
    recognized = int(job.get("recognized_invoices") or 0)
    failed = int(job.get("failed_count") or 0)

    if stage in {"parse_message", "download_attachment", "import_invoice"} and matched > 0:
        handled = imported + failed
        base += min(18.0, (handled * 18.0) / max(1, matched))
    elif stage == "trigger_recognition" and imported > 0:
        base += min(10.0, (recognized * 10.0) / max(1, imported))

    return round(min(99.0, max(0.0, base)), 2)


def _derive_final_status(job: Dict[str, Any]) -> str:
    imported = int(job.get("imported_invoices") or 0)
    failed = int(job.get("failed_count") or 0)
    if failed == 0:
        return "completed"
    if imported == 0:
        return "failed"
    return "partial_success"


def _normalize_email_job_payload(job_id: Optional[str], job: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not job_id or not job:
        return {
            "job_id": job_id,
            "task_type": "email_pull",
            "status": "not_found",
            "raw_status": "not_found",
            "user_id": None,
            "mailbox": "",
            "mailbox_folder": "INBOX",
            "time_range": "",
            "days": 0,
            "current_stage": "queued",
            "scanned_emails": 0,
            "matched_emails": 0,
            "downloaded_attachments": 0,
            "imported_invoices": 0,
            "recognized_invoices": 0,
            "failed_count": 0,
            "current_email_subject": "",
            "current_attachment_name": "",
            "current_invoice_id": None,
            "current_invoice_name": None,
            "started_at": None,
            "updated_at": _email_now(),
            "finished_at": None,
            "progress_percent": 0.0,
            "logs": [],
            "errors": [],
            "recognize_job_id": None,
            # 兼容旧前端字段
            "total": 0,
            "completed": 0,
            "failed": 0,
            "total_messages": 0,
            "matched_messages": 0,
            "downloaded": 0,
            "imported": 0,
            "result_summary": {"total": 0, "success_count": 0, "failed_count": 0},
        }

    raw_status = str(job.get("status") or "queued")
    status = raw_status
    if raw_status == "error":
        status = "failed"
    elif raw_status == "completed":
        status = _derive_final_status(job)

    scanned = int(job.get("scanned_emails") or 0)
    matched = int(job.get("matched_emails") or 0)
    downloaded = int(job.get("downloaded_attachments") or 0)
    imported = int(job.get("imported_invoices") or 0)
    recognized = int(job.get("recognized_invoices") or 0)
    failed_count = int(job.get("failed_count") or 0)
    total = max(matched, imported + failed_count)

    progress_percent = float(job.get("progress_percent") or 0.0)
    if status in _EMAIL_TERMINAL_STATUS:
        progress_percent = 100.0

    return {
        "job_id": job_id,
        "task_type": "email_pull",
        "status": status,
        "raw_status": raw_status,
        "user_id": job.get("user_id"),
        "mailbox": job.get("mailbox") or "",
        "mailbox_folder": job.get("mailbox_folder") or "INBOX",
        "time_range": job.get("time_range") or "",
        "days": int(job.get("days") or 0),
        "current_stage": job.get("current_stage") or "queued",
        "scanned_emails": scanned,
        "matched_emails": matched,
        "downloaded_attachments": downloaded,
        "imported_invoices": imported,
        "recognized_invoices": recognized,
        "failed_count": failed_count,
        "current_email_subject": job.get("current_email_subject") or "",
        "current_attachment_name": job.get("current_attachment_name") or "",
        "current_invoice_id": job.get("current_invoice_id"),
        "current_invoice_name": job.get("current_invoice_name"),
        "started_at": job.get("started_at"),
        "updated_at": job.get("updated_at"),
        "finished_at": job.get("finished_at"),
        "progress_percent": round(progress_percent, 2),
        "logs": list(job.get("logs") or []),
        "errors": list(job.get("errors") or []),
        "recognize_job_id": job.get("recognize_job_id"),
        # 兼容旧前端字段
        "total": total,
        "completed": imported,
        "failed": failed_count,
        "total_messages": scanned,
        "matched_messages": matched,
        "downloaded": downloaded,
        "imported": imported,
        "result_summary": {
            "total": total,
            "success_count": imported,
            "failed_count": failed_count,
            "recognized_invoices": recognized,
        },
    }


def _touch(job: Dict[str, Any]) -> None:
    job["updated_at"] = _email_now()
    job["progress_percent"] = _calc_progress(job)


def _set(job_id: str, **kwargs) -> None:
    with _email_jobs_lock:
        job = _email_jobs.get(job_id)
        if not job:
            return
        job.update(kwargs)
        _touch(job)


def _inc(job_id: str, **delta) -> None:
    with _email_jobs_lock:
        job = _email_jobs.get(job_id)
        if not job:
            return
        for key, value in delta.items():
            job[key] = int(job.get(key) or 0) + int(value)
        _touch(job)


def _log(job_id: str, message: str) -> None:
    with _email_jobs_lock:
        job = _email_jobs.get(job_id)
        if not job:
            return
        logs: List[str] = list(job.get("logs") or [])
        logs.append(f"{datetime.now().strftime('%H:%M:%S')} {message}")
        job["logs"] = logs[-300:]
        _touch(job)


def _error(job_id: str, message: str) -> None:
    with _email_jobs_lock:
        job = _email_jobs.get(job_id)
        if not job:
            return
        errors: List[str] = list(job.get("errors") or [])
        msg = f"{datetime.now().strftime('%H:%M:%S')} {message}"
        errors.append(msg)
        job["errors"] = errors[-100:]
        logs: List[str] = list(job.get("logs") or [])
        logs.append(f"{datetime.now().strftime('%H:%M:%S')} [错误] {message}")
        job["logs"] = logs[-300:]
        _touch(job)


def _set_stage(job_id: str, stage: str, message: Optional[str] = None) -> None:
    _set(job_id, current_stage=stage)
    if message:
        _log(job_id, message)


def start_email_push_job(user_id: str, mailbox: str, auth_code: str, days: int) -> str:
    job_id = uuid.uuid4().hex
    with _email_jobs_lock:
        _email_jobs[job_id] = {
            "job_id": job_id,
            "task_type": "email_pull",
            "status": "queued",
            "user_id": user_id,
            "mailbox": mailbox,
            "mailbox_folder": "INBOX",
            "time_range": f"last_{days}_days",
            "days": days,
            "current_stage": "queued",
            "scanned_emails": 0,
            "matched_emails": 0,
            "downloaded_attachments": 0,
            "imported_invoices": 0,
            "recognized_invoices": 0,
            "failed_count": 0,
            "current_email_subject": "",
            "current_attachment_name": "",
            "current_invoice_id": None,
            "current_invoice_name": None,
            "recognize_job_id": None,
            "logs": [],
            "errors": [],
            "started_at": _email_now(),
            "updated_at": _email_now(),
            "finished_at": None,
            "progress_percent": 0.0,
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
        return _normalize_email_job_payload(job_id, _email_jobs.get(job_id))


def get_latest_email_push_job(user_id: str) -> Dict[str, Any]:
    with _email_jobs_lock:
        matched = [(job_id, job) for job_id, job in _email_jobs.items() if job.get("user_id") == user_id]
        if not matched:
            return _normalize_email_job_payload(None, None)
        matched.sort(key=lambda item: item[1].get("updated_at") or "", reverse=True)
        job_id, job = matched[0]
        return _normalize_email_job_payload(job_id, job)


def _run_email_push_job_sync(job_id: str, user_id: str, mailbox: str, auth_code: str, days: int) -> None:
    from services import file_service

    _set(job_id, status="running")
    _set_stage(job_id, "connect_imap", "正在连接邮箱...")

    db = DatabaseManager()
    user = db.get_user_by_id(user_id)
    if not user:
        _error(job_id, "用户不存在")
        _set(job_id, status="failed", finished_at=_email_now())
        return

    host = _imap_host_for_email(mailbox)
    start_date = (datetime.now() - timedelta(days=days)).date()
    today = datetime.now().date()
    save_dir = os.path.join(config.get_upload_dir(user_id), "_email_tmp", job_id)
    os.makedirs(save_dir, exist_ok=True)

    imap = None
    matched_ids: List[bytes] = []
    imported_invoice_ids: List[str] = []

    try:
        imap = imaplib.IMAP4_SSL(host)
        imap.login(mailbox, auth_code)
        _log(job_id, f"已连接 IMAP 服务器：{host}")

        _set_stage(job_id, "select_mailbox", "正在选择邮箱文件夹 INBOX...")
        status, _ = imap.select("INBOX")
        if status != "OK":
            raise RuntimeError("选择 INBOX 失败")
        _log(job_id, "已选择 INBOX")

        _set_stage(job_id, "search_emails", "正在搜索邮件...")
        status, data = imap.search(None, "ALL")
        if status != "OK":
            raise RuntimeError("IMAP 搜索失败")
        all_ids = data[0].split() if data and data[0] else []
        _set(job_id, scanned_emails=0)
        _log(job_id, f"搜索到候选邮件 {len(all_ids)} 封")

        _set_stage(job_id, "filter_emails", "正在过滤符合条件的邮件...")
        for idx, mid in enumerate(all_ids, start=1):
            _inc(job_id, scanned_emails=1)
            try:
                status, head = imap.fetch(mid, "(BODY[HEADER.FIELDS (SUBJECT DATE)])")
                if status != "OK" or not head or not head[0] or not head[0][1]:
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
            finally:
                if idx % 50 == 0:
                    _log(job_id, f"已扫描邮件 {idx}/{len(all_ids)}")

        _set(job_id, matched_emails=len(matched_ids))
        _log(job_id, f"匹配到符合条件邮件 {len(matched_ids)} 封")

        if not matched_ids:
            _log(job_id, "未匹配到符合条件的邮件")
            _set_stage(job_id, "finalize", "正在汇总任务结果...")
            _set(job_id, status="completed", finished_at=_email_now(), current_email_subject="", current_attachment_name="")
            _log(job_id, "邮箱拉取完成（无匹配邮件）")
            return

        for idx, mid in enumerate(matched_ids, start=1):
            _set_stage(job_id, "parse_message", f"正在解析邮件 {idx}/{len(matched_ids)}...")
            try:
                status, mdata = imap.fetch(mid, "(RFC822)")
                if status != "OK" or not mdata or not mdata[0] or not mdata[0][1]:
                    _inc(job_id, failed_count=1)
                    _error(job_id, f"邮件内容读取失败：#{idx}")
                    continue

                msg = pyemail.message_from_bytes(mdata[0][1])
                subject = _safe_decode_header(msg.get("Subject", ""))
                _set(job_id, current_email_subject=subject, current_attachment_name="")
                _log(job_id, f"处理邮件：{subject or f'# {idx}'}")

                attachments: List[Tuple[str, str]] = []
                links: List[str] = []

                for part in msg.walk():
                    filename = part.get_filename()
                    content_type = (part.get_content_type() or "").lower()
                    if filename:
                        fname = _safe_decode_header(filename)
                        ext = os.path.splitext(fname.lower())[1]
                        if ext in {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".ofd", ".xml"}:
                            _set_stage(job_id, "download_attachment", f"正在下载附件：{fname}")
                            local_name = _safe_filename(f"{mid.decode(errors='ignore')}_{fname}")
                            local_path = os.path.join(save_dir, local_name)
                            payload = part.get_payload(decode=True)
                            if payload:
                                with open(local_path, "wb") as f:
                                    f.write(payload)
                                attachments.append((fname, local_path))
                                _inc(job_id, downloaded_attachments=1)
                                _log(job_id, f"附件下载成功：{fname}")
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
                            continue

                for link in links:
                    if not any(k in link.lower() for k in ["jss.com.cn", "nnfp", "invoice", "fapiao", ".pdf"]):
                        continue
                    _set_stage(job_id, "download_attachment", "正在下载邮件中的发票链接...")
                    p = _download_link_best_effort_sync(link, save_dir)
                    if p:
                        attachments.append((os.path.basename(p), p))
                        _inc(job_id, downloaded_attachments=1)
                        _log(job_id, f"链接附件下载成功：{os.path.basename(p)}")
                    else:
                        _inc(job_id, failed_count=1)
                        _error(job_id, f"链接附件下载失败：{link}")

                chosen = _group_choose_files(attachments)
                if not chosen:
                    _log(job_id, f"邮件未发现可导入附件：{subject or f'# {idx}'}")
                    continue

                for original_name, local_path in chosen:
                    _set_stage(job_id, "import_invoice", f"正在导入发票：{original_name}")
                    _set(job_id, current_attachment_name=original_name)
                    try:
                        result = asyncio_run(
                            file_service.import_local_file(
                                user_id=user_id,
                                src_path=local_path,
                                original_filename=original_name,
                            )
                        )
                        pages = (result or {}).get("pages") or []
                        added = len(pages)
                        if added <= 0:
                            _inc(job_id, failed_count=1)
                            _error(job_id, f"导入后未生成发票记录：{original_name}")
                            continue
                        ids = [str(p.get("id")) for p in pages if p.get("id")]
                        imported_invoice_ids.extend(ids)
                        _inc(job_id, imported_invoices=added)
                        _log(job_id, f"导入成功：{original_name}（新增 {added} 条）")
                    except Exception as e:
                        _inc(job_id, failed_count=1)
                        _error(job_id, f"导入失败：{original_name}，{str(e)}")
            except Exception as e:
                _inc(job_id, failed_count=1)
                _error(job_id, f"邮件处理失败：{str(e)}")

        if imported_invoice_ids:
            _set_stage(job_id, "trigger_recognition", "正在触发发票识别...")
            _log(job_id, f"待识别发票数量：{len(imported_invoice_ids)}")
            from workbench_service import workbench_service
            for idx, invoice_id in enumerate(imported_invoice_ids, start=1):
                _set(
                    job_id,
                    current_invoice_id=invoice_id,
                    current_invoice_name=f"{idx}/{len(imported_invoice_ids)}",
                )
                try:
                    asyncio_run(workbench_service.rerun_invoice(user_id, invoice_id))
                    _inc(job_id, recognized_invoices=1)
                    _log(job_id, f"识别完成：{invoice_id}")
                except Exception as e:
                    _inc(job_id, failed_count=1)
                    _error(job_id, f"识别失败：{invoice_id}，{str(e)}")
        else:
            _log(job_id, "未导入任何发票，跳过识别阶段")

        _set_stage(job_id, "finalize", "正在汇总任务结果...")
        with _email_jobs_lock:
            final_status = _derive_final_status(_email_jobs.get(job_id) or {})
        _set(
            job_id,
            status=final_status,
            finished_at=_email_now(),
            current_email_subject="",
            current_attachment_name="",
            current_invoice_id=None,
            current_invoice_name=None,
        )
        _log(job_id, "邮箱拉取任务已结束")
    except Exception as e:
        _error(job_id, f"任务异常终止：{str(e)}")
        with _email_jobs_lock:
            current = _email_jobs.get(job_id) or {}
            fallback_status = _derive_final_status(current)
            if fallback_status == "completed":
                fallback_status = "failed"
        _set(
            job_id,
            status=fallback_status,
            finished_at=_email_now(),
            current_email_subject="",
            current_attachment_name="",
            current_invoice_id=None,
            current_invoice_name=None,
        )
    finally:
        try:
            if imap:
                imap.logout()
        except Exception:
            pass
        try:
            if os.path.exists(save_dir):
                shutil.rmtree(save_dir, ignore_errors=True)
        except Exception:
            pass
