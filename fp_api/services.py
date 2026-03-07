import os
import asyncio
import shutil
import threading
from typing import Any, Dict, Optional, List
from datetime import datetime

import aiofiles
from fastapi import UploadFile, HTTPException
from config import config
from utils import (
    generate_uuid, create_user_folders, init_user_database, 
    get_file_extension, is_allowed_file, format_file_size
)
from database import DatabaseManager, UserDatabaseManager

class UserService:
    """鐢ㄦ埛鏈嶅姟"""
    
    def __init__(self):
        self.db = DatabaseManager()
    
    def register_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """鐢ㄦ埛娉ㄥ唽"""
        # 妫€鏌ョ敤鎴峰悕鍜岄偖绠辨槸鍚﹀凡瀛樺湪
        if self.db.user_exists(username=user_data['username']):
            raise HTTPException(status_code=400, detail="??????")
        
        if self.db.user_exists(email=user_data['email']):
            raise HTTPException(status_code=400, detail="?????")
        
        # 鍒涘缓鐢ㄦ埛
        user_id = self.db.create_user(user_data)
        
        create_user_folders(user_id)
        user_db_path = config.get_user_db_path(user_id)
        init_user_database(user_id, user_db_path)
        
        return {
            "user_id": user_id,
            "message": "????"
        }
    
    def login_user(self, username: str, password: str, ip_address: str = None, 
                  user_agent: str = None) -> Dict[str, Any]:
        """鐢ㄦ埛鐧诲綍"""
        from utils import hash_password, verify_password
        
        user = self.db.get_user_by_username(username)
        if not user or not verify_password(password, user['password']):
            # 璁板綍澶辫触鐧诲綍鏃ュ織
            if user:
                self.db.create_login_log(user['id'], ip_address, user_agent, 0)
            raise HTTPException(status_code=401, detail="????????")
        
        # 鏇存柊鐧诲綍鏃堕棿
        self.db.update_login_time(user['id'])
        
        # 璁板綍鎴愬姛鐧诲綍鏃ュ織
        self.db.create_login_log(user['id'], ip_address, user_agent, 1)
        
        user_info = {
            "id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "company": user['company'],
            "phone": user['phone'],
            "status": user['status'],
            "role": user['role']
        }
        
        return {
            "message": "????",
            "user": user_info
        }
    
    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """鑾峰彇鐢ㄦ埛淇℃伅"""
        user = self.db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="?????")
        
        return user
    
    def update_user_info(self, user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """鏇存柊鐢ㄦ埛淇℃伅"""
        user = self.db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="?????")
        
        # 濡傛灉鏇存柊閭锛屾鏌ユ槸鍚﹀凡瀛樺湪
        if 'email' in update_data:
            existing_user = self.db.get_user_by_username(update_data['email'])
            if existing_user and existing_user['id'] != user_id:
                raise HTTPException(status_code=400, detail="??????")
        
        # 鏇存柊鐢ㄦ埛淇℃伅
        success = self.db.update_user(user_id, update_data)
        
        if success:
            return {"message": "????????"}
        else:
            raise HTTPException(status_code=400, detail="????????")

class FileService:
    """鏂囦欢鏈嶅姟"""
    
    def __init__(self):
        self.db = DatabaseManager()

    async def import_local_file(self, user_id: str, src_path: str, original_filename: str, batch_id: Optional[str] = None) -> Dict[str, Any]:
        """??????????????? UploadFile ???????????????"""
        user = self.db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="?????")

        if not os.path.exists(src_path):
            raise HTTPException(status_code=404, detail="??????")

        file_extension = get_file_extension(original_filename)
        if not is_allowed_file(original_filename, config.ALLOWED_EXTENSIONS):
            raise HTTPException(
                status_code=400,
                detail=f"??????????????: {', ' .join(config.ALLOWED_EXTENSIONS)}",
            )

        try:
            size = os.path.getsize(src_path)
        except Exception:
            size = None

        if isinstance(size, int) and size > config.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"???????? ({format_file_size(config.MAX_FILE_SIZE)})",
            )

        file_id = generate_uuid()
        saved_filename = f"{file_id}{file_extension}"

        upload_dir = config.get_upload_dir(user_id)
        os.makedirs(upload_dir, exist_ok=True)
        dst_path = os.path.join(upload_dir, saved_filename)

        try:
            shutil.copyfile(src_path, dst_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"??????: {str(e)}")

        user_db_path = config.get_user_db_path(user_id)
        if not os.path.exists(user_db_path):
            os.makedirs(os.path.dirname(user_db_path), exist_ok=True)
            init_user_database(user_id, user_db_path)
        else:
            init_user_database(user_id, user_db_path)

        try:
            from pathlib import Path
            from image_processing import process_upload_to_pages

            processed_dir = Path(config.get_processed_dir(user_id))
            pages = process_upload_to_pages(
                upload_path=Path(dst_path),
                original_filename=original_filename,
                processed_dir=processed_dir,
                base_id=file_id,
            )
        except Exception as e:
            try:
                if os.path.exists(dst_path):
                    os.remove(dst_path)
            except Exception:
                pass
            raise HTTPException(status_code=500, detail=f"???????: {str(e)}")

        created: list[dict[str, Any]] = []
        try:
            for p in pages:
                invoice_data = {
                    'batch_id': batch_id,
                    'filename': original_filename,
                    'saved_filename': saved_filename,
                    'processed_filename': p.get('processed_filename'),  # 鐏板害鐗堟湰锛堢敤浜?OCR锛?                    'color_filename': p.get('color_filename'),  # 褰╄壊鐗堟湰锛堢敤浜庨瑙堬級
                    'original_file_path': f"/files/{user_id}/uploads/{saved_filename}",
                    'processed_file_path': f"/files/{user_id}/processed/{p.get('processed_filename')}" if p.get('processed_filename') else None,
                    'page_index': p.get('page_index'),
                    'file_type': file_extension,
                    'file_size': size or 0,
                    'recognition_status': 0,
                }
                invoice_id = UserDatabaseManager.create_invoice_record(user_id, user_db_path, invoice_data)
                created.append(
                    {
                        'id': invoice_id,
                        'filename': original_filename,
                        'saved_filename': saved_filename,
                        'processed_filename': p.get('processed_filename'),  # 鐏板害鐗堟湰
                        'color_filename': p.get('color_filename'),  # 褰╄壊鐗堟湰
                        'original_file_path': invoice_data.get('original_file_path'),
                        'processed_file_path': invoice_data.get('processed_file_path'),
                        'page_index': p.get('page_index'),
                        'file_type': file_extension,
                        'file_size': size or 0,
                        'processed_width': p.get('processed_width'),
                        'processed_height': p.get('processed_height'),
                        'processed_bytes': p.get('processed_bytes'),
                        'recognition_status': 0,
                    }
                )
        except Exception as e:
            # 鍥炴粴锛氬垹闄?processed 鏂囦欢 + upload 鏂囦欢
            try:
                for p in pages:
                    fn = p.get('processed_filename')
                    if fn:
                        candidate = os.path.join(config.get_processed_dir(user_id), fn)
                        if os.path.exists(candidate):
                            os.remove(candidate)
                if os.path.exists(dst_path):
                    os.remove(dst_path)
            except Exception:
                pass
            raise HTTPException(status_code=500, detail=f"?????????: {str(e)}")

        return {
            "file_id": file_id,
            "filename": original_filename,
            "saved_filename": saved_filename,
            "file_size": size or 0,
            "file_type": file_extension,
            "pages": created,
            "status": "imported",
            "message": "???????????????",
        }
    
    async def upload_file(self, user_id: str, file: UploadFile, batch_id: Optional[str] = None) -> Dict[str, Any]:
        """鏂囦欢涓婁紶"""
        user = self.db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="?????")
        
        if not is_allowed_file(file.filename, config.ALLOWED_EXTENSIONS):
            raise HTTPException(
                status_code=400, 
                detail=f"??????????????: {', ' .join(config.ALLOWED_EXTENSIONS)}"
            )
        
        file_content = await file.read()
        if len(file_content) > config.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"???????? ({format_file_size(config.MAX_FILE_SIZE)})"
            )
        
        file_id = generate_uuid()
        file_extension = get_file_extension(file.filename)
        saved_filename = f"{file_id}{file_extension}"
        
        # 淇濆瓨鏂囦欢
        upload_dir = config.get_upload_dir(user_id)
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, saved_filename)
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        user_db_path = config.get_user_db_path(user_id)
        if not os.path.exists(user_db_path):
            os.makedirs(os.path.dirname(user_db_path), exist_ok=True)
            init_user_database(user_id, user_db_path)
        else:
            init_user_database(user_id, user_db_path)

        try:
            from pathlib import Path
            from image_processing import process_upload_to_pages

            processed_dir = Path(config.get_processed_dir(user_id))
            pages = process_upload_to_pages(
                upload_path=Path(file_path),
                original_filename=file.filename,
                processed_dir=processed_dir,
                base_id=file_id,
            )
        except Exception as e:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
            raise HTTPException(status_code=500, detail=f"???????: {str(e)}")

        created: list[dict[str, Any]] = []
        try:
            for p in pages:
                invoice_data = {
                    'batch_id': batch_id,
                    'filename': file.filename,
                    'saved_filename': saved_filename,
                    'processed_filename': p.get('processed_filename'),
                    'original_file_path': f"/files/{user_id}/uploads/{saved_filename}",
                    'processed_file_path': f"/files/{user_id}/processed/{p.get('processed_filename')}" if p.get('processed_filename') else None,
                    'page_index': p.get('page_index'),
                    'file_type': file_extension,
                    'file_size': len(file_content),
                    'recognition_status': 0,
                }
                invoice_id = UserDatabaseManager.create_invoice_record(user_id, user_db_path, invoice_data)
                created.append(
                    {
                        'id': invoice_id,
                        'filename': file.filename,
                        'saved_filename': saved_filename,
                        'processed_filename': p.get('processed_filename'),
                        'original_file_path': invoice_data.get('original_file_path'),
                        'processed_file_path': invoice_data.get('processed_file_path'),
                        'page_index': p.get('page_index'),
                        'file_type': file_extension,
                        'file_size': len(file_content),
                        'upload_time': invoice_data.get('upload_time'),
                        'processed_width': p.get('processed_width'),
                        'processed_height': p.get('processed_height'),
                        'processed_bytes': p.get('processed_bytes'),
                        'recognition_status': 0,
                    }
                )
        except Exception as e:
            # 鍥炴粴锛氬垹闄?processed 鏂囦欢 + upload 鏂囦欢
            try:
                for p in pages:
                    fn = p.get('processed_filename')
                    if fn:
                        candidate = os.path.join(config.get_processed_dir(user_id), fn)
                        if os.path.exists(candidate):
                            os.remove(candidate)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
            raise HTTPException(status_code=500, detail=f"?????????: {str(e)}")

        print(f"[upload] user_id={user_id} db={user_db_path} pages={len(created)} upload={saved_filename}")

        return {
            "file_id": file_id,
            "filename": file.filename,
            "saved_filename": saved_filename,
            "file_size": len(file_content),
            "file_type": file_extension,
            "pages": created,
            "status": "uploaded",
            "message": "???????????????"
        }
    
    def get_user_invoices(self, user_id: str, page: int = 1, limit: int = 10, keyword: str = None, recognized_only: bool = False) -> Dict[str, Any]:
        """鑾峰彇鐢ㄦ埛鍙戠エ鍒楄〃"""
        user = self.db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="?????")
        
        # 鑾峰彇鍙戠エ鍒楄〃
        user_db_path = config.get_user_db_path(user_id)
        if not os.path.exists(user_db_path):
            return {
                "invoices": [],
                "total": 0,
                "page": page,
                "limit": limit,
                "pages": 0
            }

        # 鍏煎杩佺Щ锛氱‘淇濇柊澧炲瓧娈靛瓨鍦?        init_user_database(user_id, user_db_path)
        
        return UserDatabaseManager.get_invoices(user_id, user_db_path, page, limit, keyword, recognized_only)

    def export_invoices_excel(self, user_id: str, keyword: str = None) -> bytes:
        """瀵煎嚭鍙戠エExcel"""
        from io import BytesIO
        from openpyxl import Workbook

        result = self.get_user_invoices(user_id, page=1, limit=1000000, keyword=keyword)
        invoices = result.get('invoices', [])

        wb = Workbook()
        ws = wb.active
        ws.title = "????"

        headers = ["??", "???", "???", "???", "??", "????", "???", "????"]
        ws.append(headers)

        status_map = {0: "???", 1: "???", 2: "????"}

        for idx, inv in enumerate(invoices, start=1):
            ws.append([
                idx,
                inv.get('invoice_number') or "",
                inv.get('buyer') or "",
                inv.get('seller') or "",
                inv.get('invoice_amount') or "",
                inv.get('invoice_date') or inv.get('upload_time') or "",
                inv.get('filename') or "",
                status_map.get(inv.get('recognition_status', 0), "鏈煡"),
            ])

        out = BytesIO()
        wb.save(out)
        out.seek(0)
        return out.read()
    
    def get_invoice_detail(self, user_id: str, invoice_id: str) -> Dict[str, Any]:
        """鑾峰彇鍙戠エ璇︽儏"""
        user = self.db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="?????")
        
        # 鑾峰彇鍙戠エ璇︽儏
        user_db_path = config.get_user_db_path(user_id)
        invoice = UserDatabaseManager.get_invoice_by_id(user_id, user_db_path, invoice_id)
        
        if not invoice:
            raise HTTPException(status_code=404, detail="???????")
        
        return invoice

    def delete_invoice(self, user_id: str, invoice_id: str) -> bool:
        """???????????"""
        user_db_path = config.get_user_db_path(user_id)
        invoice = UserDatabaseManager.get_invoice_by_id(user_id, user_db_path, invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="???????")

        processed_dir = config.get_processed_dir(user_id)
        if invoice.get('processed_filename'):
            processed_path = os.path.join(processed_dir, invoice['processed_filename'])
            if os.path.exists(processed_path):
                try:
                    os.remove(processed_path)
                except Exception:
                    pass

        upload_dir = config.get_upload_dir(user_id)
        if invoice.get('saved_filename'):
            # 鍙湁褰撴病鏈夊叾浠栬褰曞紩鐢ㄨ saved_filename 鏃舵墠鍒犻櫎鍘熷鏂囦欢
            try:
                conn = UserDatabaseManager.get_connection(user_db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) as c FROM invoice_details WHERE saved_filename = ? AND id != ?",
                    (invoice['saved_filename'], invoice_id),
                )
                remain = cursor.fetchone()['c']
                conn.close()
            except Exception:
                remain = 1

            if remain == 0:
                file_path = os.path.join(upload_dir, invoice['saved_filename'])
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
        else:
            # fallback
            if invoice.get('file_type'):
                file_path = os.path.join(upload_dir, f"{invoice_id}{invoice['file_type']}")
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass

        deleted = UserDatabaseManager.delete_invoice(user_db_path, invoice_id)
        return deleted

    def batch_delete_invoices(self, user_id: str, invoice_ids: list) -> Dict[str, Any]:
        """?????????????"""
        if not invoice_ids:
            return {"deleted": 0}

        user_db_path = config.get_user_db_path(user_id)
        if not os.path.exists(user_db_path):
            return {"deleted": 0}

        upload_dir = config.get_upload_dir(user_id)
        processed_dir = config.get_processed_dir(user_id)

        # 鍏堟煡鍑烘墍鏈夌浉鍏虫枃浠跺悕
        conn = UserDatabaseManager.get_connection(user_db_path)
        cursor = conn.cursor()
        placeholders = ",".join(["?"] * len(invoice_ids))
        cursor.execute(
            f"SELECT id, saved_filename, processed_filename, file_type FROM invoice_details WHERE id IN ({placeholders})",
            invoice_ids,
        )
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            if row['processed_filename']:
                processed_path = os.path.join(processed_dir, row['processed_filename'])
                if os.path.exists(processed_path):
                    try:
                        os.remove(processed_path)
                    except Exception:
                        pass

        # 鍒犻櫎 uploads originals锛氭寜 saved_filename 鍒嗙粍锛屽彧鏈夊綋鏈鍒犻櫎瑕嗙洊浜嗚 saved_filename 鐨勫叏閮ㄨ褰曟墠鍒犻櫎鍘熷鏂囦欢
        saved_to_ids = {}
        for row in rows:
            if row['saved_filename']:
                saved_to_ids.setdefault(row['saved_filename'], set()).add(row['id'])

        for saved_filename, ids_in_batch in saved_to_ids.items():
            try:
                conn = UserDatabaseManager.get_connection(user_db_path)
                cursor = conn.cursor()
                cursor.execute(
                    f"SELECT COUNT(*) as c FROM invoice_details WHERE saved_filename = ? AND id NOT IN ({','.join(['?']*len(invoice_ids))})",
                    (saved_filename, *invoice_ids),
                )
                remain = cursor.fetchone()['c']
                conn.close()
            except Exception:
                remain = 1

            if remain == 0:
                file_path = os.path.join(upload_dir, saved_filename)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass

        deleted_count = UserDatabaseManager.delete_invoices(user_db_path, invoice_ids)
        return {"deleted": deleted_count}


# 澶栭儴璇嗗埆浠诲姟鐘舵€侊紙杩涚▼鍐咃級
_recognition_jobs: dict[str, dict] = {}
_recognition_jobs_lock = threading.Lock()
_running_recognition_scope_jobs: dict[str, str] = {}


def _recognition_scope_key(user_id: str, batch_id: Optional[str] = None) -> str:
    return f"{user_id}:{batch_id or '__all__'}"


def _recognition_now() -> str:
    return datetime.now().isoformat()


def _recognition_progress_percent(total: int, completed: int, failed: int, status: str) -> float:
    if total <= 0:
        if status in {"completed", "failed", "partial_success", "cancelled"}:
            return 100.0
        return 0.0
    handled = max(0, completed + failed)
    return round(min(100.0, (handled * 100.0) / total), 2)


def _recognition_append_log(job: Dict[str, Any], message: str) -> None:
    logs = list(job.get("logs") or [])
    logs.append(f"{datetime.now().strftime('%H:%M:%S')} {message}")
    job["logs"] = logs[-200:]


def _normalize_recognition_job_payload(job_id: Optional[str], job: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not job_id or not job:
        return {
            "job_id": job_id,
            "task_type": "recognize_batch",
            "batch_id": None,
            "status": "not_found",
            "total": 0,
            "completed": 0,
            "failed": 0,
            "progress_percent": 0.0,
            "current_invoice_id": None,
            "current_invoice_name": None,
            "started_at": None,
            "updated_at": _recognition_now(),
            "finished_at": None,
            "logs": [],
            "result_summary": {"total": 0, "success_count": 0, "failed_count": 0},
        }

    status = job.get("status") or "queued"
    total = int(job.get("total") or 0)
    completed = int(job.get("completed") or 0)
    failed = int(job.get("failed") or 0)
    payload = {
        "job_id": job_id,
        "task_type": job.get("task_type") or "recognize_batch",
        "batch_id": job.get("batch_id"),
        "status": status,
        "total": total,
        "completed": completed,
        "failed": failed,
        "progress_percent": _recognition_progress_percent(total, completed, failed, status),
        "current_invoice_id": job.get("current_invoice_id"),
        "current_invoice_name": job.get("current_invoice_name"),
        "started_at": job.get("started_at"),
        "updated_at": job.get("updated_at"),
        "finished_at": job.get("finished_at"),
        "logs": list(job.get("logs") or []),
        "result_summary": job.get("result_summary") or {
            "total": total,
            "success_count": completed,
            "failed_count": failed,
        },
    }
    return payload


async def _recognize_unrecognized_job(user_id: str, job_id: str):
    from config import config
    from external_batch_api import submit_processed_input, run_batch, wait_final_output

    with _recognition_jobs_lock:
        job = _recognition_jobs.get(job_id)
        if not job:
            return
        job["status"] = "running"
        job["updated_at"] = _recognition_now()
        _recognition_append_log(job, "识别任务开始执行")
        batch_id = job.get("batch_id")

    scope_key = _recognition_scope_key(user_id, batch_id)
    user_db_path = config.get_user_db_path(user_id)

    try:
        if not os.path.exists(user_db_path):
            with _recognition_jobs_lock:
                current = _recognition_jobs.get(job_id)
                if current:
                    current["status"] = "failed"
                    current["finished_at"] = _recognition_now()
                    current["updated_at"] = _recognition_now()
                    _recognition_append_log(current, "用户数据库不存在，任务结束")
            return

        conn = UserDatabaseManager.get_connection(user_db_path)
        cursor = conn.cursor()

        query = (
            "SELECT id, processed_filename, page_index, filename "
            "FROM invoice_details "
            "WHERE recognition_status = 0 "
            "AND processed_filename IS NOT NULL "
            "AND processed_filename != ''"
        )
        params: List[Any] = []
        if batch_id:
            query += " AND batch_id = ?"
            params.append(batch_id)
        query += " ORDER BY upload_time DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        with _recognition_jobs_lock:
            current = _recognition_jobs.get(job_id)
            if not current:
                return
            current["total"] = len(rows)
            current["updated_at"] = _recognition_now()
            _recognition_append_log(current, f"待识别发票总数：{len(rows)}")
            if len(rows) == 0:
                current["status"] = "completed"
                current["finished_at"] = _recognition_now()
                current["result_summary"] = {"total": 0, "success_count": 0, "failed_count": 0}
                _recognition_append_log(current, "没有待识别发票，任务完成")
                return

        for row in rows:
            invoice_id = row["id"]
            invoice_name = row["filename"]
            processed_filename = row["processed_filename"]
            processed_path = os.path.join(config.get_processed_dir(user_id), processed_filename)

            with _recognition_jobs_lock:
                current = _recognition_jobs.get(job_id)
                if current:
                    current["current_invoice_id"] = invoice_id
                    current["current_invoice_name"] = invoice_name
                    current["updated_at"] = _recognition_now()
                    _recognition_append_log(current, f"开始处理：{invoice_name}")

            try:
                await submit_processed_input(batch_id=invoice_id, file_path=processed_path)
                await run_batch(batch_id=invoice_id)
                final_payload = await wait_final_output(batch_id=invoice_id, interval_s=1.0, timeout_s=300.0)

                results = final_payload.get("results") or []
                result_json: Optional[dict] = None
                total_time_ms = None
                if results:
                    first = results[0] or {}
                    result_json = first.get("result_json")
                    total_time_ms = first.get("total_time_ms")

                if not isinstance(result_json, dict):
                    raise RuntimeError("识别结果为空")

                def _parse_amount(v: Any):
                    if v is None:
                        return None
                    if isinstance(v, (int, float)):
                        return float(v)
                    if isinstance(v, str):
                        s = v.strip()
                        if not s:
                            return None
                        try:
                            return float(s)
                        except Exception:
                            return None
                    return None

                invoice_amount = (
                    _parse_amount(result_json.get("total_amount_in_figures"))
                    or _parse_amount(result_json.get("total_amount"))
                )

                json_info = dict(result_json)
                if json_info.get("invoice_date") is None and json_info.get("date"):
                    json_info["invoice_date"] = json_info.get("date")

                ocr_result = {
                    "invoice_amount": invoice_amount,
                    "buyer": result_json.get("buyer_name"),
                    "seller": result_json.get("seller_name"),
                    "invoice_number": result_json.get("invoice_number"),
                    "ocr_text": None,
                    "json_info": json_info,
                    "processing_time": (total_time_ms / 1000.0) if isinstance(total_time_ms, (int, float)) else None,
                    "recognition_status": 1,
                    "total_duration_ms": total_time_ms,
                }
                await ocr_service.update_invoice_result(user_id, invoice_id, ocr_result)

                with _recognition_jobs_lock:
                    current = _recognition_jobs.get(job_id)
                    if current:
                        current["completed"] = int(current.get("completed") or 0) + 1
                        current["updated_at"] = _recognition_now()
                        invoice_no = result_json.get("invoice_number") or "未知号码"
                        _recognition_append_log(current, f"识别成功：{invoice_no}")
            except Exception as e:
                ocr_result = {
                    "invoice_amount": None,
                    "buyer": None,
                    "seller": None,
                    "invoice_number": None,
                    "ocr_text": str(e),
                    "json_info": {"error": str(e)},
                    "processing_time": None,
                    "recognition_status": 2,
                }
                try:
                    await ocr_service.update_invoice_result(user_id, invoice_id, ocr_result)
                except Exception:
                    pass

                with _recognition_jobs_lock:
                    current = _recognition_jobs.get(job_id)
                    if current:
                        current["failed"] = int(current.get("failed") or 0) + 1
                        current["updated_at"] = _recognition_now()
                        _recognition_append_log(current, f"识别失败：{invoice_name}，{str(e)}")

        with _recognition_jobs_lock:
            current = _recognition_jobs.get(job_id)
            if current:
                total = int(current.get("total") or 0)
                completed = int(current.get("completed") or 0)
                failed = int(current.get("failed") or 0)
                if failed == 0:
                    current["status"] = "completed"
                elif completed == 0 and total > 0:
                    current["status"] = "failed"
                else:
                    current["status"] = "partial_success"
                current["result_summary"] = {
                    "total": total,
                    "success_count": completed,
                    "failed_count": failed,
                }
                current["finished_at"] = _recognition_now()
                current["updated_at"] = _recognition_now()
                current["current_invoice_id"] = None
                current["current_invoice_name"] = None
                _recognition_append_log(current, "识别任务已结束")
    except Exception as e:
        with _recognition_jobs_lock:
            current = _recognition_jobs.get(job_id)
            if current:
                current["status"] = "failed"
                current["finished_at"] = _recognition_now()
                current["updated_at"] = _recognition_now()
                _recognition_append_log(current, f"任务异常：{str(e)}")
    finally:
        with _recognition_jobs_lock:
            running_id = _running_recognition_scope_jobs.get(scope_key)
            if running_id == job_id:
                _running_recognition_scope_jobs.pop(scope_key, None)


def start_recognize_unrecognized(user_id: str, batch_id: Optional[str] = None) -> Dict[str, Any]:
    scope_key = _recognition_scope_key(user_id, batch_id)

    with _recognition_jobs_lock:
        running_job_id = _running_recognition_scope_jobs.get(scope_key)
        if running_job_id:
            existing = _recognition_jobs.get(running_job_id)
            if existing and existing.get("status") in {"queued", "running"}:
                return _normalize_recognition_job_payload(running_job_id, existing)

        job_id = generate_uuid()
        now = _recognition_now()
        job = {
            "job_id": job_id,
            "task_type": "recognize_batch",
            "user_id": user_id,
            "batch_id": batch_id,
            "status": "queued",
            "total": 0,
            "completed": 0,
            "failed": 0,
            "current_invoice_id": None,
            "current_invoice_name": None,
            "started_at": now,
            "updated_at": now,
            "finished_at": None,
            "logs": [],
            "result_summary": {"total": 0, "success_count": 0, "failed_count": 0},
        }
        _recognition_append_log(job, "任务已创建，等待执行")
        _recognition_jobs[job_id] = job
        _running_recognition_scope_jobs[scope_key] = job_id

    asyncio.create_task(_recognize_unrecognized_job(user_id, job_id))
    return _normalize_recognition_job_payload(job_id, job)


def get_recognition_job(job_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    with _recognition_jobs_lock:
        job = _recognition_jobs.get(job_id)
        if not job:
            return _normalize_recognition_job_payload(job_id, None)
        if user_id and job.get("user_id") != user_id:
            return _normalize_recognition_job_payload(job_id, None)
        return _normalize_recognition_job_payload(job_id, job)


def get_latest_recognition_job(user_id: str, batch_id: Optional[str] = None) -> Dict[str, Any]:
    with _recognition_jobs_lock:
        matched: List[tuple[str, Dict[str, Any]]] = []
        for jid, job in _recognition_jobs.items():
            if job.get("user_id") != user_id:
                continue
            if batch_id is not None and job.get("batch_id") != batch_id:
                continue
            matched.append((jid, job))

        if not matched:
            return _normalize_recognition_job_payload(None, None)

        matched.sort(key=lambda item: item[1].get("updated_at") or "", reverse=True)
        job_id, job = matched[0]
        return _normalize_recognition_job_payload(job_id, job)

class OCRService:
    """OCR ??"""

    @staticmethod
    async def process_invoice(file_path: str, file_type: str) -> Dict[str, Any]:
        """???? OCR ????????"""
        import time
        import random

        start_time = time.time()
        # result = await your_ocr_service.recognize(file_path)
        await asyncio.sleep(2)
        processing_time = time.time() - start_time

        return {
            "success": True,
            "invoice_amount": random.uniform(100, 10000),
            "buyer": "????????",
            "seller": "?????????",
            "invoice_number": f"INV{random.randint(100000, 999999)}",
            "ocr_text": "?? OCR ????????...",
            "json_info": {
                "confidence": random.uniform(0.8, 0.95),
                "fields": ["????", "????", "???", "???"],
                "extracted_data": {
                    "invoice_code": f"{random.randint(10000000, 99999999)}",
                    "invoice_date": "2024-01-15",
                    "tax_amount": random.uniform(10, 1000),
                },
            },
            "processing_time": processing_time,
            "recognition_status": 1,
        }

    @staticmethod
    async def update_invoice_result(user_id: str, invoice_id: str, ocr_result: Dict[str, Any]) -> bool:
        """????????"""
        user_db_path = config.get_user_db_path(user_id)
        return UserDatabaseManager.update_invoice_recognition(
            user_id, user_db_path, invoice_id, ocr_result
        )

# ????
user_service = UserService()
file_service = FileService()
ocr_service = OCRService()
