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

def _email_now() -> str:
    return datetime.now().isoformat()


def _email_progress_percent(total: int, completed: int, failed: int, status: str) -> float:
    if total <= 0:
        if status in {"completed", "failed", "partial_success", "cancelled"}:
            return 100.0
        return 0.0
    handled = max(0, completed + failed)
    return round(min(100.0, (handled * 100.0) / total), 2)


def _normalize_email_job_payload(job_id: Optional[str], job: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not job_id or not job:
        return {
            "job_id": job_id,
            "task_type": "email_pull",
            "status": "not_found",
            "user_id": None,
            "total": 0,
            "completed": 0,
            "failed": 0,
            "progress_percent": 0.0,
            "current_invoice_id": None,
            "current_invoice_name": None,
            "started_at": None,
            "updated_at": _email_now(),
            "finished_at": None,
            "logs": [],
            "result_summary": {"total": 0, "success_count": 0, "failed_count": 0},
            "total_messages": 0,
            "matched_messages": 0,
            "downloaded": 0,
            "imported": 0,
        }

    raw_status = job.get("status") or "queued"
    matched_messages = int(job.get("matched_messages") or 0)
    downloaded = int(job.get("downloaded") or 0)
    imported = int(job.get("imported") or 0)
    failed = int(job.get("failed") or 0)
    total = max(matched_messages, downloaded, imported + failed)

    status = raw_status
    if raw_status == "error":
        status = "failed"
    elif raw_status == "completed" and failed > 0 and imported > 0:
        status = "partial_success"

    return {
        "job_id": job_id,
        "task_type": job.get("task_type") or "email_pull",
        "status": status,
        "raw_status": raw_status,
        "user_id": job.get("user_id"),
        "total": total,
        "completed": imported,
        "failed": failed,
        "progress_percent": _email_progress_percent(total, imported, failed, status),
        "current_invoice_id": job.get("current_invoice_id"),
        "current_invoice_name": job.get("current_invoice_name"),
        "started_at": job.get("started_at"),
        "updated_at": job.get("updated_at"),
        "finished_at": job.get("finished_at"),
        "logs": list(job.get("logs") or []),
        "result_summary": {
            "total": total,
            "success_count": imported,
            "failed_count": failed,
            "matched_messages": matched_messages,
            "downloaded": downloaded,
        },
        "total_messages": int(job.get("total_messages") or 0),
        "matched_messages": matched_messages,
        "downloaded": downloaded,
        "imported": imported,
    }


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
    # 榛樿鎸?QQ 閭
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
    # 鎻愬彇 href 閾炬帴
    links = re.findall(r'href=[\"\']?(https?://[^\"\'\s>]+)', html, flags=re.I)
    # 浠呬繚鐣欏彲鑳芥槸鍙戠エ涓嬭浇/骞冲彴閾炬帴
    keep: List[str] = []
    for u in links:
        if any(k in u.lower() for k in ["jss.com.cn", "nnfp", "fapiao.com", "invoice", "download", "/pdf", ".pdf"]):
            keep.append(u)
    # 鍘婚噸
    seen = set()
    out = []
    for u in keep:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


async def _download_link_best_effort(url: str, save_dir: str) -> Optional[str]:
    """????????????? None?"""
    # ???????????????
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
    """????????????????????"""
    # ??: [(filename, abs_path), ...]
    # ??: ?????????

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
            "job_id": job_id,
            "task_type": "email_pull",
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
            "current_invoice_id": None,
            "current_invoice_name": None,
            "started_at": _email_now(),
            "updated_at": _email_now(),
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
        return _normalize_email_job_payload(job_id, j)


def get_latest_email_push_job(user_id: str) -> Dict[str, Any]:
    with _email_jobs_lock:
        matched = [(job_id, job) for job_id, job in _email_jobs.items() if job.get("user_id") == user_id]
        if not matched:
            return _normalize_email_job_payload(None, None)
        matched.sort(key=lambda item: item[1].get("updated_at") or "", reverse=True)
        job_id, job = matched[0]
        return _normalize_email_job_payload(job_id, job)

def _log(job_id: str, msg: str):
    with _email_jobs_lock:
        j = _email_jobs.get(job_id)
        if not j:
            return
        logs: list = j.get("logs") or []
        logs.append(f"{datetime.now().strftime('%H:%M:%S')} {msg}")
        j["logs"] = logs[-200:]
        j["updated_at"] = _email_now()


def _set(job_id: str, **kwargs):
    with _email_jobs_lock:
        if job_id in _email_jobs:
            _email_jobs[job_id].update(kwargs)
            _email_jobs[job_id]["updated_at"] = _email_now()

def _run_email_push_job_sync(job_id: str, user_id: str, mailbox: str, auth_code: str, days: int):
    from services import file_service  # 閬垮厤寰幆 import

    _set(job_id, status="running")
    _log(job_id, "寮€濮嬫媺鍙栭偖绠遍偖浠?..")

    db = DatabaseManager()
    user = db.get_user_by_id(user_id)
    if not user:
        _set(job_id, status="failed", finished_at=_email_now())
        _log(job_id, "?????")
        return

    host = _imap_host_for_email(mailbox)
    start_date = (datetime.now() - timedelta(days=days)).date()
    today = datetime.now().date()

    save_dir = os.path.join(config.get_upload_dir(user_id), "_email_tmp", job_id)
    os.makedirs(save_dir, exist_ok=True)

    matched_ids: List[bytes] = []

    try:
        imap = imaplib.IMAP4_SSL(host)
        # imaplib 鍦?Python3 涓湡鏈涚殑鏄?str锛岃繖閲屼笉瑕佹墜鍔?encode
        imap.login(mailbox, auth_code)
        imap.select("INBOX")

        status, data = imap.search(None, "ALL")
        if status != "OK":
            raise RuntimeError("IMAP 鎼滅储澶辫触")

        all_ids = data[0].split()
        _set(job_id, total_messages=len(all_ids))
        _log(job_id, f"閭鎬婚偖浠舵暟: {len(all_ids)}")

        for mid in all_ids:
            try:
                _, head = imap.fetch(mid, "(BODY[HEADER.FIELDS (SUBJECT DATE)])")
                if not head or not head[0] or not head[0][1]:
                    continue

                msg = pyemail.message_from_bytes(head[0][1])
                subject = _safe_decode_header(msg.get("Subject", ""))
                if "鍙戠エ" not in subject:
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
        _log(job_id, f"鍛戒腑鍙戠エ涓婚閭欢: {len(matched_ids)}")

        if not matched_ids:
            _set(job_id, status="completed", finished_at=_email_now(), current_invoice_name=None, current_invoice_id=None)
            _log(job_id, "鏈壘鍒扮鍚堟潯浠剁殑鍙戠エ閭欢")
            imap.logout()
            return

        # 閫愬皝澶勭悊
        for idx, mid in enumerate(matched_ids, start=1):
            _log(job_id, f"澶勭悊閭欢 {idx}/{len(matched_ids)}")
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

                for link in links:
                    if any(k in link.lower() for k in ["jss.com.cn", "nnfp"]):
                        p = _download_link_best_effort_sync(link, save_dir)
                        if p:
                            chosen.append((os.path.basename(p), p))
                        else:
                            _log(job_id, f"璇鸿閾炬帴鏃犳硶鐩存帴涓嬭浇锛堝彲鑳介渶瑕佹祻瑙堝櫒鑷姩鍖栵級: {link}")

                if not chosen:
                    continue

                with _email_jobs_lock:
                    current_downloaded = (_email_jobs.get(job_id) or {}).get("downloaded", 0)
                _set(job_id, downloaded=current_downloaded + len(chosen))

                # 瀵煎叆锛氬鐢?upload 鐨勯澶勭悊鍏ュ簱閫昏緫
                for original_name, local_path in chosen:
                    try:
                        _set(job_id, current_invoice_name=original_name)
                        asyncio_run(file_service.import_local_file(user_id=user_id, src_path=local_path, original_filename=original_name))
                        with _email_jobs_lock:
                            current_imported = (_email_jobs.get(job_id) or {}).get("imported", 0)
                        _set(job_id, imported=current_imported + 1)
                    except Exception as e:
                        with _email_jobs_lock:
                            current_failed = (_email_jobs.get(job_id) or {}).get("failed", 0)
                        _set(job_id, failed=current_failed + 1)
                        _log(job_id, f"鍏ュ簱澶辫触: {original_name}: {str(e)}")

            except Exception as e:
                with _email_jobs_lock:
                    current_failed = (_email_jobs.get(job_id) or {}).get("failed", 0)
                _set(job_id, failed=current_failed + 1)
                _log(job_id, f"閭欢澶勭悊澶辫触: {str(e)}")

        imap.logout()
        _set(job_id, status="completed", finished_at=_email_now(), current_invoice_name=None, current_invoice_id=None)
        _log(job_id, "????????")

    except Exception as e:
        _set(job_id, status="failed", finished_at=_email_now())
        _log(job_id, f"浠诲姟澶辫触: {str(e)}")


def asyncio_run(coro):
    """??????????????"""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        # 宸插瓨鍦ㄤ簨浠跺惊鐜椂鍏滃簳
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


def _download_link_best_effort_sync(url: str, save_dir: str) -> Optional[str]:
    """??????????????"""
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

