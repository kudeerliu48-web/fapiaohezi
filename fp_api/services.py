import os
import asyncio
import shutil
from typing import Any, Dict, Optional
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
    """用户服务"""
    
    def __init__(self):
        self.db = DatabaseManager()
    
    def register_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """用户注册"""
        # 检查用户名和邮箱是否已存在
        if self.db.user_exists(username=user_data['username']):
            raise HTTPException(status_code=400, detail="用户名已存在")
        
        if self.db.user_exists(email=user_data['email']):
            raise HTTPException(status_code=400, detail="邮箱已存在")
        
        # 创建用户
        user_id = self.db.create_user(user_data)
        
        # 创建用户文件夹和数据库
        create_user_folders(user_id)
        user_db_path = config.get_user_db_path(user_id)
        init_user_database(user_id, user_db_path)
        
        return {
            "user_id": user_id,
            "message": "注册成功"
        }
    
    def login_user(self, username: str, password: str, ip_address: str = None, 
                  user_agent: str = None) -> Dict[str, Any]:
        """用户登录"""
        from utils import hash_password, verify_password
        
        user = self.db.get_user_by_username(username)
        if not user or not verify_password(password, user['password']):
            # 记录失败登录日志
            if user:
                self.db.create_login_log(user['id'], ip_address, user_agent, 0)
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        # 更新登录时间
        self.db.update_login_time(user['id'])
        
        # 记录成功登录日志
        self.db.create_login_log(user['id'], ip_address, user_agent, 1)
        
        # 返回用户信息（不包含密码）
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
            "message": "登录成功",
            "user": user_info
        }
    
    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """获取用户信息"""
        user = self.db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        return user
    
    def update_user_info(self, user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新用户信息"""
        # 检查用户是否存在
        user = self.db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 如果更新邮箱，检查是否已存在
        if 'email' in update_data:
            existing_user = self.db.get_user_by_username(update_data['email'])
            if existing_user and existing_user['id'] != user_id:
                raise HTTPException(status_code=400, detail="邮箱已被使用")
        
        # 更新用户信息
        success = self.db.update_user(user_id, update_data)
        
        if success:
            return {"message": "用户信息更新成功"}
        else:
            raise HTTPException(status_code=400, detail="没有可更新的字段")

class FileService:
    """文件服务"""
    
    def __init__(self):
        self.db = DatabaseManager()

    async def import_local_file(self, user_id: str, src_path: str, original_filename: str, batch_id: Optional[str] = None) -> Dict[str, Any]:
        """导入本地文件（用于邮箱推送等非 UploadFile 场景），处理逻辑与手动上传一致"""
        # 检查用户是否存在
        user = self.db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        if not os.path.exists(src_path):
            raise HTTPException(status_code=404, detail="源文件不存在")

        file_extension = get_file_extension(original_filename)
        if not is_allowed_file(original_filename, config.ALLOWED_EXTENSIONS):
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型。支持的类型: {', '.join(config.ALLOWED_EXTENSIONS)}",
            )

        # 读取并检查文件大小
        try:
            size = os.path.getsize(src_path)
        except Exception:
            size = None

        if isinstance(size, int) and size > config.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过限制 ({format_file_size(config.MAX_FILE_SIZE)})",
            )

        file_id = generate_uuid()
        saved_filename = f"{file_id}{file_extension}"

        upload_dir = config.get_upload_dir(user_id)
        os.makedirs(upload_dir, exist_ok=True)
        dst_path = os.path.join(upload_dir, saved_filename)

        # 复制到 uploads 目录（保持与手动上传一致的存储结构）
        try:
            shutil.copyfile(src_path, dst_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")

        # 确保用户数据库存在
        user_db_path = config.get_user_db_path(user_id)
        if not os.path.exists(user_db_path):
            os.makedirs(os.path.dirname(user_db_path), exist_ok=True)
            init_user_database(user_id, user_db_path)
        else:
            init_user_database(user_id, user_db_path)

        # 处理为 processed webp（PDF 多页拆分）
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
            raise HTTPException(status_code=500, detail=f"文件预处理失败: {str(e)}")

        created: list[dict[str, Any]] = []
        try:
            for p in pages:
                invoice_data = {
                    'batch_id': batch_id,
                    'filename': original_filename,
                    'saved_filename': saved_filename,
                    'processed_filename': p.get('processed_filename'),
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
                        'processed_filename': p.get('processed_filename'),
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
            # 回滚：删除 processed 文件 + upload 文件
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
            raise HTTPException(status_code=500, detail=f"写入用户数据库失败: {str(e)}")

        return {
            "file_id": file_id,
            "filename": original_filename,
            "saved_filename": saved_filename,
            "file_size": size or 0,
            "file_type": file_extension,
            "pages": created,
            "status": "imported",
            "message": "文件导入成功，已生成预处理图片",
        }
    
    async def upload_file(self, user_id: str, file: UploadFile, batch_id: Optional[str] = None) -> Dict[str, Any]:
        """文件上传"""
        # 检查用户是否存在
        user = self.db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 检查文件类型（仅图片 / PDF）
        if not is_allowed_file(file.filename, config.ALLOWED_EXTENSIONS):
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型。支持的类型: {', '.join(config.ALLOWED_EXTENSIONS)}"
            )
        
        # 检查文件大小
        file_content = await file.read()
        if len(file_content) > config.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过限制 ({format_file_size(config.MAX_FILE_SIZE)})"
            )
        
        # 生成文件ID和文件名（upload 原始保存）
        file_id = generate_uuid()
        file_extension = get_file_extension(file.filename)
        saved_filename = f"{file_id}{file_extension}"
        
        # 保存文件
        upload_dir = config.get_upload_dir(user_id)
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, saved_filename)
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        # 确保用户数据库存在
        user_db_path = config.get_user_db_path(user_id)
        if not os.path.exists(user_db_path):
            os.makedirs(os.path.dirname(user_db_path), exist_ok=True)
            init_user_database(user_id, user_db_path)
        else:
            # 兼容迁移：确保新增字段存在
            init_user_database(user_id, user_db_path)

        # 处理为 processed webp（PDF 多页拆分）
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
            raise HTTPException(status_code=500, detail=f"文件预处理失败: {str(e)}")

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
            # 回滚：删除 processed 文件 + upload 文件
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
            raise HTTPException(status_code=500, detail=f"写入用户数据库失败: {str(e)}")

        print(f"[upload] user_id={user_id} db={user_db_path} pages={len(created)} upload={saved_filename}")

        return {
            "file_id": file_id,
            "filename": file.filename,
            "saved_filename": saved_filename,
            "file_size": len(file_content),
            "file_type": file_extension,
            "pages": created,
            "status": "uploaded",
            "message": "文件上传成功，已生成预处理图片"
        }
    
    def get_user_invoices(self, user_id: str, page: int = 1, limit: int = 10, keyword: str = None, recognized_only: bool = False) -> Dict[str, Any]:
        """获取用户发票列表"""
        # 检查用户是否存在
        user = self.db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 获取发票列表
        user_db_path = config.get_user_db_path(user_id)
        if not os.path.exists(user_db_path):
            return {
                "invoices": [],
                "total": 0,
                "page": page,
                "limit": limit,
                "pages": 0
            }

        # 兼容迁移：确保新增字段存在
        init_user_database(user_id, user_db_path)
        
        return UserDatabaseManager.get_invoices(user_id, user_db_path, page, limit, keyword, recognized_only)

    def export_invoices_excel(self, user_id: str, keyword: str = None) -> bytes:
        """导出发票Excel"""
        from io import BytesIO
        from openpyxl import Workbook

        # 拉取全部数据（不分页）
        result = self.get_user_invoices(user_id, page=1, limit=1000000, keyword=keyword)
        invoices = result.get('invoices', [])

        wb = Workbook()
        ws = wb.active
        ws.title = "发票清单"

        headers = ["序号", "发票号", "购买方", "售卖方", "金额", "开票时间", "文件名", "识别状态"]
        ws.append(headers)

        status_map = {0: "待识别", 1: "已识别", 2: "识别失败"}

        for idx, inv in enumerate(invoices, start=1):
            ws.append([
                idx,
                inv.get('invoice_number') or "",
                inv.get('buyer') or "",
                inv.get('seller') or "",
                inv.get('invoice_amount') or "",
                inv.get('invoice_date') or inv.get('upload_time') or "",
                inv.get('filename') or "",
                status_map.get(inv.get('recognition_status', 0), "未知"),
            ])

        out = BytesIO()
        wb.save(out)
        out.seek(0)
        return out.read()
    
    def get_invoice_detail(self, user_id: str, invoice_id: str) -> Dict[str, Any]:
        """获取发票详情"""
        # 检查用户是否存在
        user = self.db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 获取发票详情
        user_db_path = config.get_user_db_path(user_id)
        invoice = UserDatabaseManager.get_invoice_by_id(user_id, user_db_path, invoice_id)
        
        if not invoice:
            raise HTTPException(status_code=404, detail="发票记录不存在")
        
        return invoice

    def delete_invoice(self, user_id: str, invoice_id: str) -> bool:
        """删除发票记录和对应文件"""
        user_db_path = config.get_user_db_path(user_id)
        invoice = UserDatabaseManager.get_invoice_by_id(user_id, user_db_path, invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="发票记录不存在")

        # 删除处理后文件（processed）
        processed_dir = config.get_processed_dir(user_id)
        if invoice.get('processed_filename'):
            processed_path = os.path.join(processed_dir, invoice['processed_filename'])
            if os.path.exists(processed_path):
                try:
                    os.remove(processed_path)
                except Exception:
                    pass

        # 删除原始文件（uploads）（注意：PDF 多页会共享同一个 saved_filename）
        upload_dir = config.get_upload_dir(user_id)
        if invoice.get('saved_filename'):
            # 只有当没有其他记录引用该 saved_filename 时才删除原始文件
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
        """批量删除发票记录和对应文件"""
        if not invoice_ids:
            return {"deleted": 0}

        user_db_path = config.get_user_db_path(user_id)
        if not os.path.exists(user_db_path):
            return {"deleted": 0}

        upload_dir = config.get_upload_dir(user_id)
        processed_dir = config.get_processed_dir(user_id)

        # 先查出所有相关文件名
        conn = UserDatabaseManager.get_connection(user_db_path)
        cursor = conn.cursor()
        placeholders = ",".join(["?"] * len(invoice_ids))
        cursor.execute(
            f"SELECT id, saved_filename, processed_filename, file_type FROM invoice_details WHERE id IN ({placeholders})",
            invoice_ids,
        )
        rows = cursor.fetchall()
        conn.close()

        # 删除 processed（每条记录一个 processed 文件）
        for row in rows:
            if row['processed_filename']:
                processed_path = os.path.join(processed_dir, row['processed_filename'])
                if os.path.exists(processed_path):
                    try:
                        os.remove(processed_path)
                    except Exception:
                        pass

        # 删除 uploads originals：按 saved_filename 分组，只有当本次删除覆盖了该 saved_filename 的全部记录才删除原始文件
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


# 外部识别任务状态（进程内）
_recognition_jobs: dict[str, dict] = {}


async def _recognize_unrecognized_job(user_id: str, job_id: str):
    from config import config
    from external_batch_api import submit_processed_input, run_batch, wait_final_output

    user_db_path = config.get_user_db_path(user_id)
    if not os.path.exists(user_db_path):
        _recognition_jobs[job_id] = {"status": "completed", "total": 0, "completed": 0, "failed": 0}
        return

    conn = UserDatabaseManager.get_connection(user_db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, processed_filename, page_index, filename FROM invoice_details WHERE recognition_status = 0 AND processed_filename IS NOT NULL AND processed_filename != '' ORDER BY upload_time DESC"
    )
    rows = cursor.fetchall()
    conn.close()

    total = len(rows)
    _recognition_jobs[job_id] = {
        "status": "running", 
        "total": total, 
        "completed": 0, 
        "failed": 0,
        "logs": [f"{datetime.now().strftime('%H:%M:%S')} 开始识别，共 {total} 张发票"]
    }
    if total == 0:
        _recognition_jobs[job_id]["status"] = "completed"
        return

    for row in rows:
        invoice_id = row["id"]
        processed_filename = row["processed_filename"]
        processed_path = os.path.join(config.get_processed_dir(user_id), processed_filename)

        try:
            await submit_processed_input(batch_id=invoice_id, file_path=processed_path)
            await run_batch(batch_id=invoice_id)
            final_payload = await wait_final_output(batch_id=invoice_id, interval_s=1.0, timeout_s=180.0)

            results = final_payload.get("results") or []
            result_json: Optional[dict] = None
            total_time_ms = None
            if results:
                first = results[0] or {}
                result_json = first.get("result_json")
                total_time_ms = first.get("total_time_ms")

            if not isinstance(result_json, dict):
                raise RuntimeError("external result_json missing")

            def _parse_amount(v):
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
            }
            await ocr_service.update_invoice_result(user_id, invoice_id, ocr_result)
            _recognition_jobs[job_id]["completed"] += 1
            _recognition_jobs[job_id]["logs"].append(
                f"{datetime.now().strftime('%H:%M:%S')} ✅ 识别成功：{result_json.get('invoice_number', 'N/A')}"
            )
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
            _recognition_jobs[job_id]["failed"] += 1
            _recognition_jobs[job_id]["logs"].append(
                f"{datetime.now().strftime('%H:%M:%S')} ❌ 识别失败：{str(e)}"
            )

    _recognition_jobs[job_id]["status"] = "completed"


def start_recognize_unrecognized(user_id: str) -> str:
    job_id = generate_uuid()
    _recognition_jobs[job_id] = {"status": "queued", "total": 0, "completed": 0, "failed": 0}
    asyncio.create_task(_recognize_unrecognized_job(user_id, job_id))
    return job_id


def get_recognition_job(job_id: str) -> dict:
    job = _recognition_jobs.get(job_id)
    if not job:
        return {"status": "not_found"}
    
    # 返回包含日志的状态信息
    return {
        "status": job.get("status"),
        "total": job.get("total", 0),
        "completed": job.get("completed", 0),
        "failed": job.get("failed", 0),
        "logs": job.get("logs", [])
    }

class OCRService:
    """OCR服务（预留接口）"""
    
    @staticmethod
    async def process_invoice(file_path: str, file_type: str) -> Dict[str, Any]:
        """
        处理发票OCR识别
        这里是预留接口，你需要对接实际的OCR平台
        """
        import time
        import random
        
        # 模拟处理时间
        start_time = time.time()
        
        # TODO: 在这里实现实际的OCR服务调用
        # 示例：
        # result = await your_ocr_service.recognize(file_path)
        
        # 模拟OCR结果
        await asyncio.sleep(2)  # 模拟处理时间
        
        processing_time = time.time() - start_time
        
        # 返回模拟结果
        return {
            "success": True,
            "invoice_amount": random.uniform(100, 10000),
            "buyer": "示例购买方公司",
            "seller": "示例销售方公司",
            "invoice_number": f"INV{random.randint(100000, 999999)}",
            "ocr_text": "这是OCR识别的文本内容...",
            "json_info": {
                "confidence": random.uniform(0.8, 0.95),
                "fields": ["发票代码", "发票号码", "开票日期", "金额"],
                "extracted_data": {
                    "invoice_code": f"{random.randint(10000000, 99999999)}",
                    "invoice_date": "2024-01-15",
                    "tax_amount": random.uniform(10, 1000)
                }
            },
            "processing_time": processing_time,
            "recognition_status": 1  # 识别成功
        }
    
    @staticmethod
    async def update_invoice_result(user_id: str, invoice_id: str, ocr_result: Dict[str, Any]) -> bool:
        """更新发票识别结果"""
        user_db_path = config.get_user_db_path(user_id)
        return UserDatabaseManager.update_invoice_recognition(
            user_id, user_db_path, invoice_id, ocr_result
        )

# 服务实例
user_service = UserService()
file_service = FileService()
ocr_service = OCRService()
