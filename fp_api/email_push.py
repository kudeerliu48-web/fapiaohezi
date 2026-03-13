import asyncio
import concurrent.futures
import imaplib
import os
import re
import shutil
import threading
import uuid
from datetime import datetime, timedelta
from email.header import decode_header
from email.message import Message
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import email as pyemail

from config import config
from database import DatabaseManager


_email_jobs: Dict[str, Dict[str, Any]] = {}
_email_jobs_lock = threading.Lock()

MAX_ATTACHMENT_WORKERS = 4
MAX_RECOGNITION_SUBMITS = 4

_recognition_submit_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=MAX_RECOGNITION_SUBMITS,
    thread_name_prefix="email-recognition",
)

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


def _parse_date_ymd(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except Exception:
        return None


def _imap_date(value: datetime) -> str:
    return value.strftime("%d-%b-%Y")


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
    submitted = int(job.get("recognition_jobs_submitted") or 0)
    failed = int(job.get("failed_count") or 0)

    if stage in {"parse_message", "download_attachment", "import_invoice"} and matched > 0:
        handled = imported + failed
        base += min(18.0, (handled * 18.0) / max(1, matched))
    elif stage == "trigger_recognition" and imported > 0:
        base += min(10.0, (submitted * 10.0) / max(1, imported))

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
            "batch_id": None,
            "user_id": None,
            "mailbox": "INBOX",
            "mailbox_account": "",
            "mailbox_folder": "INBOX",
            "time_range": "",
            "date_range_mode": "",
            "start_date": "",
            "end_date": "",
            "days": 0,
            "current_stage": "queued",
            "scanned_emails": 0,
            "matched_emails": 0,
            "downloaded_attachments": 0,
            "imported_invoices": 0,
            "recognized_invoices": 0,
            "recognition_jobs_submitted": 0,
            "pdf_attachments_found": 0,
            "pdf_attachments_downloaded": 0,
            "small_files_bypassed": 0,
            "large_files_converted_to_webp": 0,
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
    submitted = int(job.get("recognition_jobs_submitted") or 0)
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
        "batch_id": job.get("batch_id"),
        "user_id": job.get("user_id"),
        "mailbox": job.get("mailbox") or "INBOX",
        "mailbox_account": job.get("mailbox_account") or "",
        "mailbox_folder": job.get("mailbox_folder") or "INBOX",
        "time_range": job.get("time_range") or "",
        "date_range_mode": job.get("date_range_mode") or "",
        "start_date": job.get("start_date") or "",
        "end_date": job.get("end_date") or "",
        "days": int(job.get("days") or 0),
        "current_stage": job.get("current_stage") or "queued",
        "scanned_emails": scanned,
        "matched_emails": matched,
        "downloaded_attachments": downloaded,
        "imported_invoices": imported,
        "recognized_invoices": recognized,
        "recognition_jobs_submitted": submitted,
        "pdf_attachments_found": int(job.get("pdf_attachments_found") or 0),
        "pdf_attachments_downloaded": int(job.get("pdf_attachments_downloaded") or 0),
        "small_files_bypassed": int(job.get("small_files_bypassed") or 0),
        "large_files_converted_to_webp": int(job.get("large_files_converted_to_webp") or 0),
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
            "recognition_jobs_submitted": submitted,
            "pdf_attachments_found": int(job.get("pdf_attachments_found") or 0),
            "pdf_attachments_downloaded": int(job.get("pdf_attachments_downloaded") or 0),
            "small_files_bypassed": int(job.get("small_files_bypassed") or 0),
            "large_files_converted_to_webp": int(job.get("large_files_converted_to_webp") or 0),
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


def _is_pdf_part(filename: str, content_type: str) -> bool:
    ext = os.path.splitext((filename or "").lower())[1]
    ctype = (content_type or "").lower()
    if ext == ".pdf":
        return True
    if "pdf" in ctype and ext in {"", ".pdf"}:
        return True
    return False


def _parse_header_for_match(
    imap: imaplib.IMAP4_SSL,
    mid: bytes,
    start_day,
    end_day,
) -> Tuple[bool, str]:
    status, head = imap.fetch(mid, "(BODY[HEADER.FIELDS (SUBJECT DATE)])")
    if status != "OK" or not head or not head[0] or not head[0][1]:
        return False, ""

    msg = pyemail.message_from_bytes(head[0][1])
    subject = _safe_decode_header(msg.get("Subject", ""))
    if "发票" not in subject:
        return False, subject

    date_str = msg.get("Date", "")
    try:
        msg_dt = parsedate_to_datetime(date_str)
        if msg_dt.tzinfo is not None:
            msg_dt = msg_dt.astimezone().replace(tzinfo=None)
        msg_date = msg_dt.date()
    except Exception:
        return False, subject

    if not (start_day <= msg_date <= end_day):
        return False, subject
    return True, subject


def _extract_pdf_attachments_from_message(msg: Message) -> List[Tuple[str, bytes]]:
    pdf_parts: List[Tuple[str, bytes]] = []
    for part in msg.walk():
        filename = part.get_filename()
        if not filename:
            continue
        decoded_name = _safe_decode_header(filename)
        content_type = (part.get_content_type() or "").lower()
        if not _is_pdf_part(decoded_name, content_type):
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        if not decoded_name.lower().endswith(".pdf"):
            decoded_name = f"{decoded_name}.pdf"
        pdf_parts.append((decoded_name, payload))
    return pdf_parts


def _recognize_invoice_worker(job_id: str, user_id: str, invoice_id: str, invoice_name: str) -> None:
    from workbench_service import workbench_service

    try:
        asyncio_run(workbench_service.rerun_invoice(user_id, invoice_id))
    except Exception as e:
        _error(job_id, f"识别执行失败：{invoice_name} ({invoice_id}) - {str(e)}")


def _submit_recognition_async(job_id: str, user_id: str, invoice_id: str, invoice_name: str) -> None:
    try:
        _set_stage(job_id, "trigger_recognition", "正在提交识别任务...")
        _recognition_submit_executor.submit(_recognize_invoice_worker, job_id, user_id, invoice_id, invoice_name)
        _inc(job_id, recognition_jobs_submitted=1, recognized_invoices=1)
        _set(job_id, current_invoice_id=invoice_id, current_invoice_name=invoice_name)
        _log(job_id, f"已提交识别任务：{invoice_name} ({invoice_id})")
    except Exception as e:
        _inc(job_id, failed_count=1)
        _error(job_id, f"提交识别任务失败：{invoice_name} - {str(e)}")


def _process_single_attachment(
    job_id: str,
    user_id: str,
    batch_id: str,
    file_service,
    save_dir: str,
    message_token: str,
    attachment_name: str,
    payload: bytes,
) -> None:
    _set_stage(job_id, "download_attachment", f"正在下载附件：{attachment_name}")
    _set(job_id, current_attachment_name=attachment_name)

    local_name = _safe_filename(f"{message_token}_{attachment_name}")
    local_path = os.path.join(save_dir, local_name)
    with open(local_path, "wb") as f:
        f.write(payload)

    _inc(job_id, downloaded_attachments=1, pdf_attachments_downloaded=1)
    _log(job_id, f"附件下载成功：{attachment_name}")

    _set_stage(job_id, "import_invoice", f"正在导入发票：{attachment_name}")
    result = asyncio_run(
        file_service.import_local_file(
            user_id=user_id,
            src_path=local_path,
            original_filename=attachment_name,
            batch_id=batch_id,
            email_pipeline=True,
        )
    )
    pages = (result or {}).get("pages") or []
    added = len(pages)
    if added <= 0:
        raise RuntimeError("导入后未生成发票记录")

    small_bypassed = int((result or {}).get("small_file_bypassed") or 0)
    large_webp = int((result or {}).get("large_file_converted_to_webp") or 0)
    _inc(
        job_id,
        imported_invoices=added,
        small_files_bypassed=small_bypassed,
        large_files_converted_to_webp=large_webp,
    )

    _log(job_id, f"导入成功：{attachment_name}（新增 {added} 张）")
    try:
        from workbench_service import workbench_service
        workbench_service.refresh_batch(user_id, batch_id)
    except Exception:
        pass

    for page in pages:
        invoice_id = str(page.get("id") or "").strip()
        if not invoice_id:
            continue
        invoice_name = page.get("filename") or attachment_name
        _submit_recognition_async(job_id, user_id, invoice_id, invoice_name)


def _process_single_message(
    job_id: str,
    user_id: str,
    batch_id: str,
    message_bytes: bytes,
    message_token: str,
    save_dir: str,
) -> None:
    from services import file_service

    _set_stage(job_id, "parse_message", "正在解析邮件内容...")
    msg = pyemail.message_from_bytes(message_bytes)
    subject = _safe_decode_header(msg.get("Subject", ""))
    _set(job_id, current_email_subject=subject, current_attachment_name="")

    pdf_parts = _extract_pdf_attachments_from_message(msg)
    if not pdf_parts:
        _log(job_id, f"邮件无 PDF 附件：{subject or message_token}")
        return

    _inc(job_id, pdf_attachments_found=len(pdf_parts))
    for attachment_name, payload in pdf_parts:
        try:
            _process_single_attachment(
                job_id=job_id,
                user_id=user_id,
                batch_id=batch_id,
                file_service=file_service,
                save_dir=save_dir,
                message_token=message_token,
                attachment_name=attachment_name,
                payload=payload,
            )
        except Exception as e:
            _inc(job_id, failed_count=1)
            _error(job_id, f"附件处理失败：{attachment_name} - {str(e)}")


def start_email_push_job(
    user_id: str,
    mailbox: str,
    auth_code: str,
    days: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    date_range_mode: Optional[str] = None,
) -> str:
    job_id = uuid.uuid4().hex
    with _email_jobs_lock:
        _email_jobs[job_id] = {
            "job_id": job_id,
            "task_type": "email_pull",
            "status": "queued",
            "batch_id": None,
            "user_id": user_id,
            "mailbox": "INBOX",
            "mailbox_account": mailbox,
            "mailbox_folder": "INBOX",
            "time_range": f"last_{days}_days",
            "date_range_mode": date_range_mode or f"last_{days}_days",
            "start_date": start_date or "",
            "end_date": end_date or "",
            "days": days,
            "current_stage": "queued",
            "scanned_emails": 0,
            "matched_emails": 0,
            "downloaded_attachments": 0,
            "imported_invoices": 0,
            "recognized_invoices": 0,
            "recognition_jobs_submitted": 0,
            "pdf_attachments_found": 0,
            "pdf_attachments_downloaded": 0,
            "small_files_bypassed": 0,
            "large_files_converted_to_webp": 0,
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
        args=(job_id, user_id, mailbox, auth_code, days, start_date, end_date),
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


def _run_email_push_job_sync(
    job_id: str,
    user_id: str,
    mailbox: str,
    auth_code: str,
    days: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> None:
    _set(job_id, status="running")
    _set_stage(job_id, "connect_imap", "正在连接邮箱...")

    db = DatabaseManager()
    user = db.get_user_by_id(user_id)
    if not user:
        _inc(job_id, failed_count=1)
        _error(job_id, "用户不存在")
        _set(job_id, status="failed", finished_at=_email_now())
        return

    try:
        from workbench_service import workbench_service
        email_batch_id = workbench_service.create_batch(user_id, remark="??????")
        _set(job_id, batch_id=email_batch_id)
        _log(job_id, f"??????????{email_batch_id}")
    except Exception as e:
        _inc(job_id, failed_count=1)
        _error(job_id, f"???????????{str(e)}")
        _set(job_id, status="failed", finished_at=_email_now())
        return

    host = _imap_host_for_email(mailbox)
    start_dt = _parse_date_ymd(start_date)
    end_dt = _parse_date_ymd(end_date)
    if not end_dt:
        end_dt = datetime.now()
    if not start_dt:
        start_dt = end_dt - timedelta(days=days)
    if start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt

    start_day = start_dt.date()
    end_day = end_dt.date()
    end_plus_one = end_dt + timedelta(days=1)

    _set(job_id, start_date=start_day.isoformat(), end_date=end_day.isoformat())
    save_dir = os.path.join(config.get_upload_dir(user_id), "_email_tmp", job_id)
    os.makedirs(save_dir, exist_ok=True)

    imap = None
    futures: List[concurrent.futures.Future] = []
    matched_count = 0

    try:
        imap = imaplib.IMAP4_SSL(host)
        imap.login(mailbox, auth_code)
        _log(job_id, f"已连接 IMAP 服务：{host}")

        _set_stage(job_id, "select_mailbox", "正在选择邮箱文件夹 INBOX...")
        status, _ = imap.select("INBOX")
        if status != "OK":
            raise RuntimeError("选择 INBOX 失败")
        _log(job_id, "当前邮箱文件夹：INBOX")
        _log(job_id, f"生效日期范围：{start_day.isoformat()} 至 {end_day.isoformat()}")

        _set_stage(job_id, "search_emails", "正在搜索指定日期范围邮件...")
        search_since = _imap_date(start_dt)
        search_before = _imap_date(end_plus_one)
        _log(job_id, f"IMAP SEARCH 条件：SINCE {search_since} BEFORE {search_before}")
        status, data = imap.search(None, "SINCE", search_since, "BEFORE", search_before)
        if status != "OK":
            raise RuntimeError("IMAP 搜索失败")
        all_ids = data[0].split() if data and data[0] else []
        _log(job_id, f"服务端候选邮件数量：{len(all_ids)}")

        _set_stage(job_id, "filter_emails", "正在本地二次过滤邮件...")
        attachment_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=MAX_ATTACHMENT_WORKERS,
            thread_name_prefix=f"email-attachment-{job_id[:6]}",
        )
        try:
            for idx, mid in enumerate(all_ids, start=1):
                _inc(job_id, scanned_emails=1)
                try:
                    matched, subject = _parse_header_for_match(imap, mid, start_day, end_day)
                    if not matched:
                        continue
                    matched_count += 1
                    _inc(job_id, matched_emails=1)
                    _set(job_id, current_email_subject=subject or "", current_attachment_name="")

                    status, mdata = imap.fetch(mid, "(RFC822)")
                    if status != "OK" or not mdata or not mdata[0] or not mdata[0][1]:
                        _inc(job_id, failed_count=1)
                        _error(job_id, f"读取邮件正文失败：{subject or mid.decode(errors='ignore')}")
                        continue

                    message_bytes = mdata[0][1]
                    message_token = mid.decode(errors="ignore") or f"msg_{idx}"
                    futures.append(
                        attachment_executor.submit(
                            _process_single_message,
                            job_id,
                            user_id,
                            email_batch_id,
                            message_bytes,
                            message_token,
                            save_dir,
                        )
                    )
                except Exception as e:
                    _inc(job_id, failed_count=1)
                    _error(job_id, f"邮件过滤失败：{str(e)}")
                finally:
                    if idx % 50 == 0:
                        _log(job_id, f"已扫描邮件 {idx}/{len(all_ids)}")

            _log(job_id, f"本地二次过滤后邮件数量：{matched_count}")
            _log(job_id, f"最终进入附件处理邮件数量：{matched_count}")

            if matched_count == 0:
                _log(job_id, "未匹配到符合条件的邮件")

            if futures:
                for future in concurrent.futures.as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        _inc(job_id, failed_count=1)
                        _error(job_id, f"附件工作线程失败：{str(e)}")
        finally:
            attachment_executor.shutdown(wait=True, cancel_futures=False)

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
        _inc(job_id, failed_count=1)
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
