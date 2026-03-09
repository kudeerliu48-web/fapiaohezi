from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
import os
import sqlite3
import shutil
from datetime import datetime, timedelta

from models import (
    UserCreate, UserLogin, UserUpdate, UserResponse,
    InvoiceDetail, FileUploadResponse, ApiResponse, PaginatedResponse,
    BatchDeleteRequest
)
from services import user_service, file_service, ocr_service
from services import start_recognize_unrecognized, get_recognition_job, get_latest_recognition_job
from utils import ResponseHelper
from database import DatabaseManager
from config import config
from workbench_service import workbench_service

from email_push import start_email_push_job, get_email_push_job, get_latest_email_push_job

api_router = APIRouter(prefix="/api", tags=["API"])

# 鐢ㄦ埛鐩稿叧璺敱
@api_router.post("/register", response_model=ApiResponse)
async def register(user: UserCreate):
    """鐢ㄦ埛娉ㄥ唽"""
    try:
        from utils import hash_password
        user_data = user.dict()
        user_data['password'] = hash_password(user.password)
        
        result = user_service.register_user(user_data)
        return ResponseHelper.success(result, "娉ㄥ唽鎴愬姛")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)

@api_router.post("/login", response_model=ApiResponse)
async def login(user: UserLogin):
    """鐢ㄦ埛鐧诲綍"""
    try:
        result = user_service.login_user(user.username, user.password)
        return ResponseHelper.success(result, "鐧诲綍鎴愬姛")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)

@api_router.get("/user/{user_id}", response_model=ApiResponse)
async def get_user(user_id: str):
    """鑾峰彇鐢ㄦ埛淇℃伅"""
    try:
        user = user_service.get_user_info(user_id)
        return ResponseHelper.success(user, "鑾峰彇鐢ㄦ埛淇℃伅鎴愬姛")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)

@api_router.put("/user/{user_id}", response_model=ApiResponse)
async def update_user(user_id: str, user_update: UserUpdate):
    """鏇存柊鐢ㄦ埛淇℃伅"""
    try:
        update_data = {k: v for k, v in user_update.dict().items() if v is not None}
        result = user_service.update_user_info(user_id, update_data)
        return ResponseHelper.success(result, "鏇存柊鐢ㄦ埛淇℃伅鎴愬姛")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)

# 鏂囦欢鐩稿叧璺敱
@api_router.post("/upload/{user_id}", response_model=ApiResponse)
async def upload_file(user_id: str, file: UploadFile = File(...)):
    """鏂囦欢涓婁紶"""
    try:
        result = await file_service.upload_file(user_id, file)

        return ResponseHelper.success(result, "鏂囦欢涓婁紶鎴愬姛")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


# 工作台：上传并创建批次
@api_router.post("/workbench/batches/{user_id}/upload", response_model=ApiResponse)
async def wb_upload_batch(
    user_id: str,
    files: List[UploadFile] = File(...),
    remark: Optional[str] = Form(None),
):
    try:
        result = await workbench_service.upload_and_create_batch(user_id, files, remark)
        return ResponseHelper.success(result, "Batch created")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


@api_router.get("/workbench/batches/{user_id}", response_model=ApiResponse)
async def wb_get_batches(user_id: str, page: int = 1, limit: int = 10, status: Optional[str] = None):
    try:
        data = workbench_service.get_batches(user_id, page, limit, status)
        return ResponseHelper.success(data, "鑾峰彇鎵规鍒楄〃鎴愬姛")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


@api_router.get("/workbench/batch/{user_id}/{batch_id}", response_model=ApiResponse)
async def wb_get_batch_detail(user_id: str, batch_id: str):
    try:
        data = workbench_service.get_batch_detail(user_id, batch_id)
        return ResponseHelper.success(data, "鑾峰彇鎵规璇︽儏鎴愬姛")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


@api_router.get("/workbench/batch/{user_id}/{batch_id}/invoices", response_model=ApiResponse)
async def wb_get_batch_invoices(
    user_id: str,
    batch_id: str,
    page: int = 1,
    limit: int = 10,
    keyword: Optional[str] = None,
    recognition_status: Optional[int] = None,
):
    try:
        data = workbench_service.get_batch_invoices(user_id, batch_id, page, limit, keyword, recognition_status)
        return ResponseHelper.success(data, "鑾峰彇鎵规鍙戠エ鍒楄〃鎴愬姛")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


@api_router.get("/workbench/invoices/{user_id}", response_model=ApiResponse)
async def wb_get_invoice_history(
    user_id: str,
    page: int = 1,
    limit: int = 20,
    keyword: Optional[str] = None,
    batch_id: Optional[str] = None,
    recognition_status: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    try:
        data = workbench_service.get_invoice_history(
            user_id=user_id,
            page=page,
            limit=limit,
            keyword=keyword,
            batch_id=batch_id,
            recognition_status=recognition_status,
            date_from=date_from,
            date_to=date_to,
        )
        return ResponseHelper.success(data, "鑾峰彇鍘嗗彶娓呭崟鎴愬姛")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


@api_router.get("/workbench/invoice/{user_id}/{invoice_id}", response_model=ApiResponse)
async def wb_get_invoice_detail(user_id: str, invoice_id: str):
    try:
        data = workbench_service.get_invoice_detail(user_id, invoice_id)
        return ResponseHelper.success(data, "鑾峰彇鍙戠エ璇︽儏鎴愬姛")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


@api_router.get("/workbench/invoice/{user_id}/{invoice_id}/steps", response_model=ApiResponse)
async def wb_get_invoice_steps(user_id: str, invoice_id: str):
    try:
        data = workbench_service.get_invoice_steps(user_id, invoice_id)
        return ResponseHelper.success(data, "鑾峰彇澶勭悊姝ラ鎴愬姛")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


@api_router.post("/workbench/invoice/{user_id}/{invoice_id}/retry", response_model=ApiResponse)
async def wb_retry_invoice(user_id: str, invoice_id: str):
    try:
        data = await workbench_service.rerun_invoice(user_id, invoice_id)
        return ResponseHelper.success(data, "閲嶈瘯璇嗗埆鎴愬姛")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


@api_router.post("/workbench/batch/{user_id}/{batch_id}/retry", response_model=ApiResponse)
async def wb_retry_batch(user_id: str, batch_id: str):
    try:
        data = await workbench_service.rerun_batch(user_id, batch_id)
        return ResponseHelper.success(data, "鎵规閲嶈瘯璇嗗埆瀹屾垚")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


@api_router.delete("/workbench/invoice/{user_id}/{invoice_id}", response_model=ApiResponse)
async def wb_delete_invoice(user_id: str, invoice_id: str):
    try:
        data = workbench_service.delete_invoice(user_id, invoice_id)
        return ResponseHelper.success(data, "鍒犻櫎鍙戠エ鎴愬姛")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


@api_router.delete("/workbench/batch/{user_id}/{batch_id}", response_model=ApiResponse)
async def wb_delete_batch(user_id: str, batch_id: str):
    try:
        data = workbench_service.delete_batch(user_id, batch_id)
        return ResponseHelper.success(data, "鍒犻櫎鎵规鎴愬姛")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


@api_router.delete("/workbench/history/{user_id}/all", response_model=ApiResponse)
async def wb_clear_history(user_id: str):
    try:
        data = workbench_service.clear_all_history(user_id)
        return ResponseHelper.success(data, "历史记录已清空")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


@api_router.get("/workbench/overview/{user_id}", response_model=ApiResponse)
async def wb_overview(user_id: str):
    try:
        data = workbench_service.get_overview_stats(user_id)
        return ResponseHelper.success(data, "鑾峰彇鎬昏缁熻鎴愬姛")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


@api_router.post("/workbench/recognize-unrecognized", response_model=ApiResponse)
async def wb_recognize_unrecognized(payload: Dict[str, Any] = Body(...)):
    """工作台：启动待识别发票识别任务"""
    try:
        user_id = (payload.get("user_id") or "").strip()
        batch_id = (payload.get("batch_id") or "").strip() or None
        if not user_id:
            return ResponseHelper.error("user_id不能为空", 400)
        user_service.get_user_info(user_id)
        task = start_recognize_unrecognized(user_id, batch_id=batch_id)
        return ResponseHelper.success(task, "Task submitted")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


@api_router.get("/workbench/recognize-status/{job_id}", response_model=ApiResponse)
async def wb_recognize_status(job_id: str, user_id: Optional[str] = None):
    """工作台：查询识别任务状态"""
    try:
        return ResponseHelper.success(get_recognition_job(job_id, user_id=user_id), "获取识别任务状态成功")
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


@api_router.get("/workbench/recognize-latest/{user_id}", response_model=ApiResponse)
async def wb_recognize_latest(user_id: str, batch_id: Optional[str] = None):
    """工作台：查询用户最近识别任务（可按批次）"""
    try:
        return ResponseHelper.success(get_latest_recognition_job(user_id, batch_id=batch_id), "获取最近识别任务成功")
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


@api_router.post("/recognize/{user_id}/unrecognized", response_model=ApiResponse)
# Deprecated: legacy API????? /api/workbench/recognize-unrecognized
async def recognize_unrecognized(user_id: str, batch_id: Optional[str] = None):
    """提交所有未识别发票（recognition_status=0）进行识别"""
    try:
        task = start_recognize_unrecognized(user_id, batch_id=batch_id)
        return ResponseHelper.success(task, "识别任务已开始")
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


@api_router.get("/recognize/status/{job_id}", response_model=ApiResponse)
# Deprecated: legacy API????? /api/workbench/recognize-status/{job_id}
async def recognize_status(job_id: str, user_id: Optional[str] = None):
    """查询识别任务状态"""
    try:
        return ResponseHelper.success(get_recognition_job(job_id, user_id=user_id), "获取识别任务状态成功")
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)
@api_router.get("/invoices/{user_id}", response_model=ApiResponse)
# Deprecated: legacy API????? /api/workbench/invoices/{user_id}
async def get_invoices(user_id: str, page: int = 1, limit: int = 10, keyword: Optional[str] = None, recognized_only: bool = False):
    """鑾峰彇鐢ㄦ埛鍙戠エ鍒楄〃"""
    try:
        result = file_service.get_user_invoices(user_id, page, limit, keyword, recognized_only)
        return ResponseHelper.success(result, "鑾峰彇鍙戠エ鍒楄〃鎴愬姛")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


def _resolve_range_days(range_key: str) -> Optional[int]:
    range_days_map = {
        "7d": 7,
        "1m": 30,
        "3m": 90,
        "6m": 180,
        "12m": 365,
    }
    return range_days_map.get(range_key)


def _resolve_email_date_range(
    range_key: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
) -> Dict[str, Any]:
    today = datetime.now().date()

    if start_date or end_date:
        if not (start_date and end_date):
            raise HTTPException(status_code=400, detail="自定义日期范围必须同时提供开始日期和结束日期")
        try:
            start_day = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_day = datetime.strptime(end_date, "%Y-%m-%d").date()
        except Exception:
            raise HTTPException(status_code=400, detail="日期格式错误，必须为 YYYY-MM-DD")
        if start_day > end_day:
            raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")
        days = max(1, (end_day - start_day).days + 1)
        return {
            "days": days,
            "date_range_mode": "custom",
            "start_date": start_day.isoformat(),
            "end_date": end_day.isoformat(),
        }

    resolved_range_key = (range_key or "3m").strip()
    days = _resolve_range_days(resolved_range_key)
    if not days:
        raise HTTPException(status_code=400, detail=f"不支持的时间范围: {resolved_range_key}")
    start_day = today - timedelta(days=days)
    return {
        "days": days,
        "date_range_mode": f"last_{resolved_range_key}",
        "start_date": start_day.isoformat(),
        "end_date": today.isoformat(),
    }


def _start_email_push_task(
    user_id: str,
    range_key: Optional[str],
    mailbox: Optional[str],
    auth_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    date_range = _resolve_email_date_range(range_key, start_date, end_date)
    days = int(date_range["days"])

    user = user_service.get_user_info(user_id)
    resolved_mailbox = (mailbox or user.get("email") or "").strip()
    if not resolved_mailbox:
        raise HTTPException(status_code=400, detail="邮箱不能为空")
    if not auth_code:
        raise HTTPException(status_code=400, detail="授权码不能为空")

    job_id = start_email_push_job(
        user_id=user_id,
        mailbox=resolved_mailbox,
        auth_code=auth_code,
        days=days,
        start_date=date_range["start_date"],
        end_date=date_range["end_date"],
        date_range_mode=date_range["date_range_mode"],
    )
    return get_email_push_job(job_id)


@api_router.post("/workbench/email-push/{user_id}/start", response_model=ApiResponse)
async def wb_start_email_push(
    user_id: str,
    range_key: str = Form("3m"),
    mailbox: Optional[str] = Form(None),
    auth_code: str = Form(...),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
):
    """工作台：启动邮箱拉取任务"""
    try:
        task = _start_email_push_task(user_id, range_key, mailbox, auth_code, start_date, end_date)
        return ResponseHelper.success(task, "邮箱任务已开始")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


@api_router.get("/workbench/email-push/status/{job_id}", response_model=ApiResponse)
async def wb_get_email_push_status(job_id: str, user_id: Optional[str] = None):
    """工作台：查询邮箱拉取任务状态"""
    try:
        task = get_email_push_job(job_id)
        if user_id and task.get("status") != "not_found" and task.get("user_id") not in (None, user_id):
            task = {"status": "not_found", "job_id": job_id}
        return ResponseHelper.success(task, "获取邮箱任务状态成功")
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


@api_router.get("/workbench/email-push/latest/{user_id}", response_model=ApiResponse)
async def wb_get_latest_email_push(user_id: str):
    """工作台：查询用户最近邮箱拉取任务"""
    try:
        return ResponseHelper.success(get_latest_email_push_job(user_id), "获取最近邮箱任务成功")
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


@api_router.post("/email-push/{user_id}/start", response_model=ApiResponse)
async def start_email_push(
    user_id: str,
    range_key: str = Form("3m"),
    mailbox: Optional[str] = Form(None),
    auth_code: str = Form(...),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
):
    """邮箱推送：拉取邮件发票附件并入库"""
    try:
        task = _start_email_push_task(user_id, range_key, mailbox, auth_code, start_date, end_date)
        return ResponseHelper.success(task, "邮箱推送任务已开始")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


@api_router.get("/email-push/status/{job_id}", response_model=ApiResponse)
async def get_email_push_status(job_id: str, user_id: Optional[str] = None):
    """查询邮箱推送任务状态"""
    try:
        task = get_email_push_job(job_id)
        if user_id and task.get("status") != "not_found" and task.get("user_id") not in (None, user_id):
            task = {"status": "not_found", "job_id": job_id}
        return ResponseHelper.success(task, "获取邮箱推送任务状态成功")
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)

@api_router.delete("/invoice/{user_id}/{invoice_id}", response_model=ApiResponse)
async def delete_invoice(user_id: str, invoice_id: str):
    """鍒犻櫎鍙戠エ锛堝悓鏃跺垹闄ゆ枃浠跺拰鏁版嵁搴撹褰曪級"""
    try:
        result = file_service.delete_invoice(user_id, invoice_id)
        return ResponseHelper.success({"deleted": result}, "鍒犻櫎鎴愬姛")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


@api_router.post("/invoices/{user_id}/batch-delete", response_model=ApiResponse)
async def batch_delete_invoices(user_id: str, req: BatchDeleteRequest):
    """鎵归噺鍒犻櫎鍙戠エ锛堝悓鏃跺垹闄ゆ枃浠跺拰鏁版嵁搴撹褰曪級"""
    try:
        result = file_service.batch_delete_invoices(user_id, req.invoice_ids)
        return ResponseHelper.success(result, "鎵归噺鍒犻櫎鎴愬姛")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)


@api_router.get("/invoices/{user_id}/export")
async def export_invoices(user_id: str, keyword: Optional[str] = None):
    """瀵煎嚭鍙戠エExcel"""
    try:
        content = file_service.export_invoices_excel(user_id, keyword)
        filename = "invoices.xlsx"
        headers = {
            "Content-Disposition": f"attachment; filename={filename}"
        }
        return StreamingResponse(
            iter([content]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers,
        )
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)

@api_router.get("/invoice/{user_id}/{invoice_id}", response_model=ApiResponse)
async def get_invoice_detail(user_id: str, invoice_id: str):
    """鑾峰彇鍙戠エ璇︽儏"""
    try:
        result = file_service.get_invoice_detail(user_id, invoice_id)
        return ResponseHelper.success(result, "鑾峰彇鍙戠エ璇︽儏鎴愬姛")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)

# 管理员相关路由
@api_router.get("/admin/users", response_model=ApiResponse)
async def get_all_users(page: int = 1, limit: int = 10):
    """鑾峰彇鎵€鏈夌敤鎴峰垪琛紙绠＄悊鍛橈級"""
    try:
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        offset = (page - 1) * limit
        cursor.execute('''
            SELECT id, username, email, company, phone, status, 
                   register_time, last_login_time, avatar_url, role
            FROM users 
            ORDER BY register_time DESC 
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        users = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT COUNT(*) as total FROM users")
        total = cursor.fetchone()['total']
        
        conn.close()
        
        return ResponseHelper.success({
            'users': users,
            'total': total,
            'page': page,
            'limit': limit,
            'pages': (total + limit - 1) // limit
        }, "鑾峰彇鐢ㄦ埛鍒楄〃鎴愬姛")
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)

@api_router.delete("/admin/user/{user_id}", response_model=ApiResponse)
async def delete_user(user_id: str):
    """删除用户（管理员）"""
    try:
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        user_db_path = config.get_user_db_path(user_id)
        if os.path.exists(user_db_path):
            os.remove(user_db_path)
        
        user_dir = config.get_user_dir(user_id)
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)
        
        # 鍒犻櫎鐢ㄦ埛璁板綍
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        
        return ResponseHelper.success({"deleted": True}, "鍒犻櫎鐢ㄦ埛鎴愬姛")
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)

@api_router.get("/admin/invoices", response_model=ApiResponse)
async def get_all_invoices(page: int = 1, limit: int = 10, keyword: Optional[str] = None):
    """获取所有发票列表（管理员）"""
    try:
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        offset = (page - 1) * limit
        
        where_clauses = []
        params = []
        
        if keyword:
            like = f"%{keyword}%"
            params.extend([like, like, like, like])
            where_clauses.append("(invoice_number LIKE ? OR buyer LIKE ? OR seller LIKE ? OR filename LIKE ?)")
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        cursor.execute("SELECT id FROM users")
        all_users = cursor.fetchall()
        
        all_invoices = []
        for user in all_users:
            user_id = user['id']
            user_db_path = config.get_user_db_path(user_id)
            if os.path.exists(user_db_path):
                user_conn = sqlite3.connect(user_db_path)
                user_conn.row_factory = sqlite3.Row
                user_cursor = user_conn.cursor()
                
                query = f'''
                    SELECT id, filename, invoice_amount, buyer, seller, invoice_number,
                           recognition_status, processing_time, upload_time, file_type, file_size
                    FROM invoice_details 
                    {where_sql}
                    ORDER BY upload_time DESC 
                    LIMIT ? OFFSET ?
                '''
                
                user_cursor.execute(query, (*params, limit, offset))
                invoices = [dict(row) for row in user_cursor.fetchall()]
                all_invoices.extend(invoices)
                
                user_conn.close()
        
        # 璁＄畻鎬绘暟
        total = len(all_invoices)
        
        # 鍒嗛〉
        start = offset
        end = offset + limit
        paginated_invoices = all_invoices[start:end]
        
        conn.close()
        
        return ResponseHelper.success({
            'invoices': paginated_invoices,
            'total': total,
            'page': page,
            'limit': limit,
            'pages': (total + limit - 1) // limit
        }, "鑾峰彇鍙戠エ鍒楄〃鎴愬姛")
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)

@api_router.get("/admin/invoice-stats", response_model=ApiResponse)
async def get_admin_invoice_stats():
    """鑾峰彇绠＄悊鍛樼粺璁′俊鎭?"""
    try:
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users")
        all_users = cursor.fetchall()
        
        total_invoices = 0
        recognized_invoices = 0
        total_amount = 0.0
        
        for user in all_users:
            user_id = user['id']
            user_db_path = config.get_user_db_path(user_id)
            if os.path.exists(user_db_path):
                user_conn = sqlite3.connect(user_db_path)
                # 杩斿洖 dict 椋庢牸琛岋紝鏀寔 row['count']
                user_conn.row_factory = sqlite3.Row
                user_cursor = user_conn.cursor()
                
                user_cursor.execute("SELECT COUNT(*) as count FROM invoice_details")
                row_total = user_cursor.fetchone()
                total_invoices += (row_total['count'] if row_total and row_total['count'] is not None else 0)
                
                user_cursor.execute("SELECT COUNT(*) as count FROM invoice_details WHERE recognition_status = 1")
                row_rec = user_cursor.fetchone()
                recognized_invoices += (row_rec['count'] if row_rec and row_rec['count'] is not None else 0)
                
                user_cursor.execute("SELECT SUM(invoice_amount) as amount FROM invoice_details WHERE invoice_amount IS NOT NULL")
                result = user_cursor.fetchone()
                if result and result['amount'] is not None:
                    total_amount += result['amount']
                
                user_conn.close()
        
        conn.close()
        
        stats = {
            "total_invoices": total_invoices,
            "recognized_invoices": recognized_invoices,
            "pending_invoices": total_invoices - recognized_invoices,
            "total_amount": round(total_amount, 2),
            "recognition_rate": round((recognized_invoices / total_invoices * 100) if total_invoices > 0 else 0, 2)
        }
        
        return ResponseHelper.success(stats, "鑾峰彇缁熻淇℃伅鎴愬姛")
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)

@api_router.get("/admin/stats", response_model=ApiResponse)
async def get_admin_stats():
    """鑾峰彇绠＄悊鍛樼患鍚堢粺璁′俊鎭?"""
    try:
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 鐢ㄦ埛缁熻
        cursor.execute("SELECT COUNT(*) as count FROM users")
        total_users = cursor.fetchone()['count']
        
        conn.close()
        
        # 鍙戠エ缁熻
        invoice_stats_result = await get_admin_invoice_stats()
        invoice_stats = invoice_stats_result.get('data', {})
        
        stats = {
            "total_users": total_users,
            **invoice_stats
        }
        
        return ResponseHelper.success(stats, "鑾峰彇缁熻淇℃伅鎴愬姛")
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)

@api_router.get("/invoice/detail/{invoice_id}", response_model=ApiResponse)
async def get_invoice_detail_admin(invoice_id: str):
    """鑾峰彇鍙戠エ璇︽儏锛堢鐞嗗憳锛?"""
    try:
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 鏌ヨ鎵€鏈夌敤鎴锋壘鍒拌鍙戠エ
        cursor.execute("SELECT id FROM users")
        all_users = cursor.fetchall()
        
        for user in all_users:
            user_id = user['id']
            user_db_path = config.get_user_db_path(user_id)
            if os.path.exists(user_db_path):
                user_conn = sqlite3.connect(user_db_path)
                user_conn.row_factory = sqlite3.Row
                user_cursor = user_conn.cursor()
                
                user_cursor.execute("SELECT * FROM invoice_details WHERE id = ?", (invoice_id,))
                invoice = user_cursor.fetchone()
                
                if invoice:
                    result = dict(invoice)
                    # 闄勫姞鐢ㄦ埛ID锛屾柟渚垮墠绔瀯閫犳枃浠跺湴鍧€
                    result["user_id"] = user_id
                    # 鏋勯€犻瑙堟枃浠禪RL锛堜紭鍏堜娇鐢ㄥ鐞嗗悗鐨勫浘鐗囷級
                    saved = result.get("saved_filename")
                    processed = result.get("processed_filename")
                    if processed:
                        file_url = f"/files/{user_id}/processed/{processed}"
                    elif saved:
                        file_url = f"/files/{user_id}/uploads/{saved}"
                    else:
                        ftype = result.get("file_type") or ""
                        file_url = f"/files/{user_id}/uploads/{invoice_id}{ftype}"
                    result["file_url"] = file_url

                    user_conn.close()
                    conn.close()
                    return ResponseHelper.success(result, "鑾峰彇鍙戠エ璇︽儏鎴愬姛")
                
                user_conn.close()
        
        conn.close()
        return ResponseHelper.error("鍙戠エ涓嶅瓨鍦?", 404)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)

@api_router.delete("/invoice/{invoice_id}", response_model=ApiResponse)
async def delete_invoice_admin(invoice_id: str):
    """鍒犻櫎鍙戠エ锛堢鐞嗗憳锛?"""
    try:
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 鏌ヨ鎵€鏈夌敤鎴锋壘鍒拌鍙戠エ
        cursor.execute("SELECT id FROM users")
        all_users = cursor.fetchall()
        
        deleted_count = 0
        for user in all_users:
            user_id = user['id']
            user_db_path = config.get_user_db_path(user_id)
            if os.path.exists(user_db_path):
                user_conn = sqlite3.connect(user_db_path)
                user_cursor = user_conn.cursor()
                
                # 鏌ユ壘鍙戠エ
                user_cursor.execute("SELECT * FROM invoice_details WHERE id = ?", (invoice_id,))
                invoice = user_cursor.fetchone()
                
                if invoice:
                    # 鍒犻櫎鏂囦欢
                    if invoice.get('saved_filename'):
                        saved_path = os.path.join(config.get_upload_dir(user_id), invoice['saved_filename'])
                        if os.path.exists(saved_path):
                            os.remove(saved_path)
                    
                    if invoice.get('processed_filename'):
                        processed_path = os.path.join(config.get_processed_dir(user_id), invoice['processed_filename'])
                        if os.path.exists(processed_path):
                            os.remove(processed_path)
                    
                    user_cursor.execute("DELETE FROM invoice_details WHERE id = ?", (invoice_id,))
                    user_conn.commit()
                    deleted_count += 1
                
                user_conn.close()
        
        conn.close()
        
        return ResponseHelper.success({"deleted": deleted_count > 0}, "鍒犻櫎鎴愬姛")
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)

# OCR 鐩稿叧璺敱
@api_router.post("/ocr/{user_id}/{invoice_id}", response_model=ApiResponse)
async def process_ocr(user_id: str, invoice_id: str):
    """鎵嬪姩瑙﹀彂OCR璇嗗埆"""
    try:
        # 鑾峰彇鍙戠エ淇℃伅
        invoice = file_service.get_invoice_detail(user_id, invoice_id)
        
        # 构建文件路径（优先使用 processed 图片）
        if invoice.get('processed_filename'):
            file_path = os.path.join(config.get_processed_dir(user_id), invoice['processed_filename'])
            file_extension = '.webp'
        elif invoice.get('saved_filename'):
            file_path = os.path.join(config.get_upload_dir(user_id), invoice['saved_filename'])
            file_extension = os.path.splitext(invoice['saved_filename'])[1]
        else:
            file_path = os.path.join(config.get_upload_dir(user_id), f"{invoice_id}{invoice['file_type']}")
            file_extension = invoice.get('file_type') or ''
        
        if not os.path.exists(file_path):
            return ResponseHelper.error("鏂囦欢涓嶅瓨鍦?", 404)
        
        # 鎵цOCR璇嗗埆
        ocr_result = await ocr_service.process_invoice(file_path, file_extension)
        
        # 鏇存柊璇嗗埆缁撴灉
        success = await ocr_service.update_invoice_result(user_id, invoice_id, ocr_result)
        
        if success:
            return ResponseHelper.success(ocr_result, "OCR璇嗗埆瀹屾垚")
        else:
            return ResponseHelper.error("鏇存柊璇嗗埆缁撴灉澶辫触", 500)
            
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)

# 绯荤粺鐩稿叧璺敱
@api_router.get("/health", response_model=ApiResponse)
async def health_check():
    """鍋ュ悍妫€鏌?"""
    from datetime import datetime
    return ResponseHelper.success({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }, "绯荤粺杩愯姝ｅ父")

@api_router.get("/stats/{user_id}", response_model=ApiResponse)
async def get_user_stats(user_id: str):
    """鑾峰彇鐢ㄦ埛缁熻淇℃伅"""
    try:
        # 鑾峰彇鍙戠エ缁熻
        invoices_result = file_service.get_user_invoices(user_id, 1, 1000)
        invoices = invoices_result.get('invoices', [])
        
        total_count = len(invoices)
        recognized_count = len([inv for inv in invoices if inv['recognition_status'] == 1])
        pending_count = len([inv for inv in invoices if inv['recognition_status'] == 0])
        failed_count = len([inv for inv in invoices if inv['recognition_status'] == 2])
        
        total_amount = sum([
            inv.get('invoice_amount', 0) for inv in invoices 
            if inv.get('invoice_amount')
        ])
        
        stats = {
            "total_invoices": total_count,
            "recognized_invoices": recognized_count,
            "pending_invoices": pending_count,
            "failed_invoices": failed_count,
            "total_amount": total_amount,
            "recognition_rate": (recognized_count / total_count * 100) if total_count > 0 else 0
        }
        
        return ResponseHelper.success(stats, "鑾峰彇缁熻淇℃伅鎴愬姛")
        
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败: {str(e)}", 500)

# 寮傛OCR澶勭悊鍑芥暟
async def process_ocr_async(user_id: str, invoice_id: str, file: UploadFile):
    """寮傛澶勭悊OCR璇嗗埆"""
    try:
        from config import config
        import os
        
        # 绛夊緟鏂囦欢瀹屽叏鍐欏叆
        await asyncio.sleep(1)
        
        invoice = file_service.get_invoice_detail(user_id, invoice_id)
        if invoice.get('processed_filename'):
            file_path = os.path.join(config.get_processed_dir(user_id), invoice['processed_filename'])
            file_extension = '.webp'
        elif invoice.get('saved_filename'):
            file_path = os.path.join(config.get_upload_dir(user_id), invoice['saved_filename'])
            file_extension = os.path.splitext(invoice['saved_filename'])[1]
        else:
            file_extension = os.path.splitext(file.filename)[1]
            file_path = os.path.join(config.get_upload_dir(user_id), f"{invoice_id}{file_extension}")
        
        # 鎵цOCR璇嗗埆
        if os.path.exists(file_path):
            ocr_result = await ocr_service.process_invoice(file_path, file_extension)
            await ocr_service.update_invoice_result(user_id, invoice_id, ocr_result)
            print(f"OCR璇嗗埆瀹屾垚: 鐢ㄦ埛{user_id}, 鍙戠エ{invoice_id}")
        
    except Exception as e:
        print(f"寮傛OCR澶勭悊澶辫触: {str(e)}")

# 瀵煎叆asyncio
import asyncio





