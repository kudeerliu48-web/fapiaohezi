from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
import re
import os
import sqlite3
import shutil
from datetime import datetime, timedelta

from models import (
    UserCreate, UserLogin, UserLoginBySMS, SmsCodeSendRequest, UserUpdate, UserResponse,
    InvoiceDetail, FileUploadResponse, ApiResponse, PaginatedResponse,
    BatchDeleteRequest
)
from services import user_service, file_service, ocr_service
from services import start_recognize_unrecognized, get_recognition_job, get_latest_recognition_job
from utils import ResponseHelper
from database import DatabaseManager, UserDatabaseManager
from config import config
from workbench_service import workbench_service
from email_push import start_email_push_job, get_email_push_job, get_latest_email_push_job
from sms_service import sms_service

api_router = APIRouter(prefix="/api", tags=["API"])

# 正则表达式模式
PHONE_PATTERN = re.compile(r"^1\d{10}$")


def _resolve_phone_value(username: Optional[str], phone: Optional[str]) -> str:
    resolved = (phone or username or "").strip()
    if not resolved:
        raise HTTPException(status_code=400, detail="手机号不能为空")
    if not PHONE_PATTERN.match(resolved):
        raise HTTPException(status_code=400, detail="手机号格式不正确")
    return resolved


@api_router.post("/auth/register", response_model=ApiResponse)
@api_router.post("/register", response_model=ApiResponse)
async def register(user: UserCreate):
    """注册（手机号作为账号）。"""
    try:
        from utils import hash_password

        phone = _resolve_phone_value(user.username, user.phone)
        if len((user.password or "")) < 6:
            return ResponseHelper.error("密码长度不能少于6位", 400)

        sms_code = (user.sms_code or "").strip()
        if sms_code and not sms_service.verify_code(phone, sms_code, purpose="register", consume=True):
            return ResponseHelper.error("验证码错误或已过期", 400)

        user_data = {
            "username": phone,
            "phone": phone,
            "password": hash_password(user.password),
            "email": user.email,
            "company": user.company,
        }
        result = user_service.register_user(user_data)
        return ResponseHelper.success(result, "注册成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"注册失败: {str(e)}", 500)


@api_router.post("/auth/login-by-password", response_model=ApiResponse)
@api_router.post("/login", response_model=ApiResponse)
async def login(user: UserLogin):
    """手机号+密码登录。"""
    try:
        phone = _resolve_phone_value(user.username, user.phone)
        result = user_service.login_user(phone, user.password)
        return ResponseHelper.success(result, "登录成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"登录失败: {str(e)}", 500)


@api_router.post("/auth/send-sms-code", response_model=ApiResponse)
async def send_sms_code(payload: SmsCodeSendRequest):
    """发送短信验证码（阿里云接口预留）。"""
    try:
        phone = _resolve_phone_value(payload.phone, payload.phone)
        purpose = (payload.purpose or "login").strip() or "login"
        if purpose not in {"login", "register"}:
            purpose = "login"
        data = sms_service.send_code(phone, purpose=purpose)
        return ResponseHelper.success(data, "验证码已发送")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"发送验证码失败: {str(e)}", 500)


@api_router.post("/auth/login-by-sms", response_model=ApiResponse)
async def login_by_sms(payload: UserLoginBySMS):
    """手机号+验证码登录。"""
    try:
        phone = _resolve_phone_value(payload.phone, payload.phone)
        if not sms_service.verify_code(phone, payload.sms_code, purpose="login", consume=True):
            return ResponseHelper.error("验证码错误或已过期", 400)

        user = user_service.db.get_user_by_username(phone)
        if not user:
            return ResponseHelper.error("手机号未注册", 404)

        user_service.db.update_login_time(user["id"])
        user_service.db.create_login_log(user["id"], None, "sms", 1)

        user_info = {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "company": user["company"],
            "phone": user.get("phone") or user["username"],
            "status": user["status"],
            "role": user["role"],
        }
        return ResponseHelper.success({"message": "登录成功", "user": user_info}, "登录成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"短信登录失败: {str(e)}", 500)


@api_router.get("/user/{user_id}", response_model=ApiResponse)
async def get_user(user_id: str):
    """获取用户信息。"""
    try:
        user = user_service.get_user_info(user_id)
        return ResponseHelper.success(user, "获取用户信息成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)

@api_router.put("/user/{user_id}", response_model=ApiResponse)
async def update_user(user_id: str, user_update: UserUpdate):
    """更新用户信息。"""
    try:
        update_data = {k: v for k, v in user_update.dict().items() if v is not None}
        result = user_service.update_user_info(user_id, update_data)
        return ResponseHelper.success(result, "更新用户信息成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)

# 文件上传
@api_router.post("/upload/{user_id}", response_model=ApiResponse)
async def upload_file(user_id: str, file: UploadFile = File(...)):
    """上传文件。"""
    try:
        result = await file_service.upload_file(user_id, file)

        return ResponseHelper.success(result, "上传文件成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


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
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


@api_router.get("/workbench/batches/{user_id}", response_model=ApiResponse)
async def wb_get_batches(user_id: str, page: int = 1, limit: int = 10, status: Optional[str] = None):
    try:
        data = workbench_service.get_batches(user_id, page, limit, status)
        return ResponseHelper.success(data, "閼惧嘲褰囬幍瑙勵偧閸掓銆冮幋鎰")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


@api_router.get("/workbench/batch/{user_id}/{batch_id}", response_model=ApiResponse)
async def wb_get_batch_detail(user_id: str, batch_id: str):
    try:
        data = workbench_service.get_batch_detail(user_id, batch_id)
        return ResponseHelper.success(data, "閼惧嘲褰囬幍瑙勵偧鐠囷附鍎忛幋鎰")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


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
        return ResponseHelper.success(data, "閼惧嘲褰囬幍瑙勵偧閸欐垹銈ㄩ崚妤勩€冮幋鎰")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


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
        return ResponseHelper.success(data, "获取发票历史清单成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


@api_router.get("/workbench/invoice/{user_id}/{invoice_id}", response_model=ApiResponse)
async def wb_get_invoice_detail(user_id: str, invoice_id: str):
    try:
        data = workbench_service.get_invoice_detail(user_id, invoice_id)
        return ResponseHelper.success(data, "获取发票详情成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


@api_router.get("/workbench/invoice/{user_id}/{invoice_id}/steps", response_model=ApiResponse)
async def wb_get_invoice_steps(user_id: str, invoice_id: str):
    try:
        data = workbench_service.get_invoice_steps(user_id, invoice_id)
        return ResponseHelper.success(data, "获取发票处理步骤成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


@api_router.post("/workbench/invoice/{user_id}/{invoice_id}/retry", response_model=ApiResponse)
async def wb_retry_invoice(user_id: str, invoice_id: str):
    try:
        data = await workbench_service.rerun_invoice(user_id, invoice_id)
        return ResponseHelper.success(data, "重试成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


@api_router.post("/workbench/batch/{user_id}/{batch_id}/retry", response_model=ApiResponse)
async def wb_retry_batch(user_id: str, batch_id: str):
    try:
        data = await workbench_service.rerun_batch(user_id, batch_id)
        return ResponseHelper.success(data, "批量重试成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


@api_router.delete("/workbench/invoice/{user_id}/{invoice_id}", response_model=ApiResponse)
async def wb_delete_invoice(user_id: str, invoice_id: str):
    try:
        data = workbench_service.delete_invoice(user_id, invoice_id)
        return ResponseHelper.success(data, "删除发票成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


@api_router.delete("/workbench/batch/{user_id}/{batch_id}", response_model=ApiResponse)
async def wb_delete_batch(user_id: str, batch_id: str):
    try:
        data = workbench_service.delete_batch(user_id, batch_id)
        return ResponseHelper.success(data, "删除批次成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


@api_router.delete("/workbench/history/{user_id}/all", response_model=ApiResponse)
async def wb_clear_history(user_id: str):
    try:
        data = workbench_service.clear_all_history(user_id)
        return ResponseHelper.success(data, "历史记录已清空")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


@api_router.get("/workbench/overview/{user_id}", response_model=ApiResponse)
async def wb_overview(user_id: str):
    try:
        data = workbench_service.get_overview_stats(user_id)
        return ResponseHelper.success(data, "閼惧嘲褰囬幀鏄忣潔缂佺喕顓搁幋鎰")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


@api_router.post("/workbench/recognize-unrecognized", response_model=ApiResponse)
async def wb_recognize_unrecognized(payload: Dict[str, Any] = Body(...)):
    """宸ヤ綔鍙帮細鍚姩寰呰瘑鍒彂绁ㄨ瘑鍒换鍔?"""
    try:
        user_id = (payload.get("user_id") or "").strip()
        batch_id = (payload.get("batch_id") or "").strip() or None
        if not user_id:
            return ResponseHelper.error("user_id涓嶈兘涓虹┖", 400)
        user_service.get_user_info(user_id)
        task = start_recognize_unrecognized(user_id, batch_id=batch_id)
        return ResponseHelper.success(task, "Task submitted")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


@api_router.get("/workbench/recognize-status/{job_id}", response_model=ApiResponse)
async def wb_recognize_status(job_id: str, user_id: Optional[str] = None):
    """宸ヤ綔鍙帮細鏌ヨ璇嗗埆浠诲姟鐘舵€?"""
    try:
        return ResponseHelper.success(get_recognition_job(job_id, user_id=user_id), "鑾峰彇璇嗗埆浠诲姟鐘舵€佹垚鍔?")
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


@api_router.get("/workbench/recognize-latest/{user_id}", response_model=ApiResponse)
async def wb_recognize_latest(user_id: str, batch_id: Optional[str] = None):
    """宸ヤ綔鍙帮細鏌ヨ鐢ㄦ埛鏈€杩戣瘑鍒换鍔★紙鍙寜鎵规锛?"""
    try:
        return ResponseHelper.success(get_latest_recognition_job(user_id, batch_id=batch_id), "鑾峰彇鏈€杩戣瘑鍒换鍔℃垚鍔?")
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


@api_router.post("/recognize/{user_id}/unrecognized", response_model=ApiResponse)
# Deprecated: legacy API????? /api/workbench/recognize-unrecognized
async def recognize_unrecognized(user_id: str, batch_id: Optional[str] = None):
    """鎻愪氦鎵€鏈夋湭璇嗗埆鍙戠エ锛坮ecognition_status=0锛夎繘琛岃瘑鍒?"""
    try:
        task = start_recognize_unrecognized(user_id, batch_id=batch_id)
        return ResponseHelper.success(task, "璇嗗埆浠诲姟宸插紑濮?")
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


@api_router.get("/recognize/status/{job_id}", response_model=ApiResponse)
# Deprecated: legacy API????? /api/workbench/recognize-status/{job_id}
async def recognize_status(job_id: str, user_id: Optional[str] = None):
    """鏌ヨ璇嗗埆浠诲姟鐘舵€?"""
    try:
        return ResponseHelper.success(get_recognition_job(job_id, user_id=user_id), "鑾峰彇璇嗗埆浠诲姟鐘舵€佹垚鍔?")
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)
@api_router.get("/invoices/{user_id}", response_model=ApiResponse)
# Deprecated: legacy API????? /api/workbench/invoices/{user_id}
async def get_invoices(user_id: str, page: int = 1, limit: int = 10, keyword: Optional[str] = None, recognized_only: bool = False):
    """閼惧嘲褰囬悽銊﹀煕閸欐垹銈ㄩ崚妤勩€?"""
    try:
        result = file_service.get_user_invoices(user_id, page, limit, keyword, recognized_only)
        return ResponseHelper.success(result, "閼惧嘲褰囬崣鎴犮偍閸掓銆冮幋鎰")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)




def _resolve_submit_user_id(user_id: Optional[str]) -> str:
    db = DatabaseManager()
    if user_id:
        user = db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="?????")
        return user_id

    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users ORDER BY register_time ASC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="????????????")
    return row["id"]


def _resolve_batch_owner_user_id(batch_id: str, user_id: Optional[str]) -> str:
    if user_id:
        return _resolve_submit_user_id(user_id)

    db = DatabaseManager()
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users")
    users = [row["id"] for row in cursor.fetchall()]
    conn.close()

    for uid in users:
        user_db_path = config.get_user_db_path(uid)
        if not os.path.exists(user_db_path):
            continue
        try:
            user_conn = UserDatabaseManager.get_connection(user_db_path)
            user_cursor = user_conn.cursor()
            user_cursor.execute("SELECT id FROM batches WHERE id = ? LIMIT 1", (batch_id,))
            row = user_cursor.fetchone()
            user_conn.close()
            if row:
                return uid
        except Exception:
            continue

    raise HTTPException(status_code=404, detail="?????")


def _map_invoice_runtime_status(row: Dict[str, Any]) -> str:
    rec_status = row.get("recognition_status")
    if rec_status == 1:
        return "success"
    if rec_status == 2:
        return "failed"
    return "processing"


def _to_stream_result_item(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "file_name": row.get("file_name") or row.get("filename"),
        "status": _map_invoice_runtime_status(row),
        "invoice_number": row.get("invoice_number"),
        "invoice_date": row.get("invoice_date"),
        "buyer_name": row.get("buyer_name") or row.get("buyer"),
        "seller_name": row.get("seller_name") or row.get("seller"),
        "service_name": row.get("service_name"),
        "amount": row.get("amount_without_tax") if row.get("amount_without_tax") is not None else row.get("invoice_amount"),
        "tax": row.get("tax_amount"),
        "total_with_tax": row.get("total_with_tax") if row.get("total_with_tax") is not None else row.get("invoice_amount"),
        "error_message": row.get("error_message") if row.get("recognition_status") == 2 else None,
        "invoice_id": row.get("invoice_id") or row.get("id"),
        "updated_at": row.get("updated_at"),
    }


@api_router.post("/invoices/submit", response_model=ApiResponse)
async def submit_invoices(
    files: List[UploadFile] = File(...),
    api_key: str = Form(""),
    user_id: Optional[str] = Form(None),
):
    """
    提交发票文件批量上传接口
    - files: 发票文件列表（支持多张/多类型文件，如PDF、图片等）
    - api_key: 接口密钥（预留参数，暂未校验）
    - user_id: 上传用户ID，不传则自动匹配系统中首个注册用户
    """
    try:
        _ = api_key
        resolved_user_id = _resolve_submit_user_id(user_id)
        result = await workbench_service.upload_and_create_batch(resolved_user_id, files, remark=None)
        batch = result.get("batch") or {}
        submitted_files = [{"file_name": f.filename} for f in files]
        payload = {
            "batch_id": batch.get("id"),
            "file_count": len(submitted_files),
            "files": submitted_files,
            "batch": batch,
            "created_count": result.get("created_count", 0),
            "failed_count": result.get("failed_count", 0),
            "failed_files": result.get("failed_files") or [],
        }
        return ResponseHelper.success(payload, "批量发票上传创建成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"????: {str(e)}", 500)


@api_router.get("/invoices/batches/{batch_id}/stream", response_model=ApiResponse)
async def get_batch_stream(
    batch_id: str,
    user_id: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    keyword: Optional[str] = None,
    file_name: Optional[str] = None,
    recognition_status: Optional[int] = None,
):

    try:
        owner_user_id = _resolve_batch_owner_user_id(batch_id, user_id)
        batch = workbench_service.get_batch_detail(owner_user_id, batch_id)
        query_page = 1 if file_name else page
        query_limit = 100000 if file_name else limit
        invoice_page = workbench_service.get_batch_invoices(
            owner_user_id,
            batch_id,
            query_page,
            query_limit,
            keyword,
            recognition_status,
        )
        rows = invoice_page.get("invoices") or []
        if file_name:
            rows = [r for r in rows if (r.get("filename") or r.get("file_name")) == file_name]
        task_summary = get_latest_recognition_job(owner_user_id, batch_id=batch_id)
        if task_summary.get("status") == "not_found":
            task_summary = None

        filtered_total = len(rows) if file_name else invoice_page.get("total", len(rows))
        completed_files = int(batch.get("success_count") or 0)
        failed_files = int(batch.get("failed_count") or 0)
        total_files = int(batch.get("total_invoices") or invoice_page.get("total") or 0)
        batch_status = batch.get("status") or ("processing" if completed_files + failed_files < total_files else "completed")

        payload = {
            "batch_id": batch_id,
            "user_id": owner_user_id,
            "status": batch_status,
            "total_files": total_files,
            "completed_files": completed_files,
            "failed_files": failed_files,
            "page": 1 if file_name else invoice_page.get("page", page),
            "limit": len(rows) if file_name else invoice_page.get("limit", limit),
            "total": filtered_total,
            "pages": 1 if file_name else invoice_page.get("pages", 1),
            "invoices": rows,
            "results": [_to_stream_result_item(row) for row in rows],
            "batch": batch,
            "task_summary": task_summary,
        }
        return ResponseHelper.success(payload, "鑾峰彇鎵规娴佹垚鍔?")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"???????: {str(e)}", 500)


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
            raise HTTPException(status_code=400, detail="鑷畾涔夋棩鏈熻寖鍥村繀椤诲悓鏃舵彁渚涘紑濮嬫棩鏈熷拰缁撴潫鏃ユ湡")
        try:
            start_day = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_day = datetime.strptime(end_date, "%Y-%m-%d").date()
        except Exception:
            raise HTTPException(status_code=400, detail="鏃ユ湡鏍煎紡閿欒锛屽繀椤讳负 YYYY-MM-DD")
        if start_day > end_day:
            raise HTTPException(status_code=400, detail="寮€濮嬫棩鏈熶笉鑳芥櫄浜庣粨鏉熸棩鏈?")
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
        raise HTTPException(status_code=400, detail=f"涓嶆敮鎸佺殑鏃堕棿鑼冨洿: {resolved_range_key}")
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
        raise HTTPException(status_code=400, detail="閭涓嶈兘涓虹┖")
    if not auth_code:
        raise HTTPException(status_code=400, detail="鎺堟潈鐮佷笉鑳戒负绌?")

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
    """宸ヤ綔鍙帮細鍚姩閭鎷夊彇浠诲姟"""
    try:
        task = _start_email_push_task(user_id, range_key, mailbox, auth_code, start_date, end_date)
        return ResponseHelper.success(task, "閭浠诲姟宸插紑濮?")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


@api_router.get("/workbench/email-push/status/{job_id}", response_model=ApiResponse)
async def wb_get_email_push_status(job_id: str, user_id: Optional[str] = None):
    """宸ヤ綔鍙帮細鏌ヨ閭鎷夊彇浠诲姟鐘舵€?"""
    try:
        task = get_email_push_job(job_id)
        if user_id and task.get("status") != "not_found" and task.get("user_id") not in (None, user_id):
            task = {"status": "not_found", "job_id": job_id}
        return ResponseHelper.success(task, "鑾峰彇閭浠诲姟鐘舵€佹垚鍔?")
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


@api_router.get("/workbench/email-push/latest/{user_id}", response_model=ApiResponse)
async def wb_get_latest_email_push(user_id: str):
    """宸ヤ綔鍙帮細鏌ヨ鐢ㄦ埛鏈€杩戦偖绠辨媺鍙栦换鍔?"""
    try:
        return ResponseHelper.success(get_latest_email_push_job(user_id), "鑾峰彇鏈€杩戦偖绠变换鍔℃垚鍔?")
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


@api_router.post("/email-push/{user_id}/start", response_model=ApiResponse)
async def start_email_push(
    user_id: str,
    range_key: str = Form("3m"),
    mailbox: Optional[str] = Form(None),
    auth_code: str = Form(...),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
):
    """閭鎺ㄩ€侊細鎷夊彇閭欢鍙戠エ闄勪欢骞跺叆搴?"""
    try:
        task = _start_email_push_task(user_id, range_key, mailbox, auth_code, start_date, end_date)
        return ResponseHelper.success(task, "閭鎺ㄩ€佷换鍔″凡寮€濮?")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


@api_router.get("/email-push/status/{job_id}", response_model=ApiResponse)
async def get_email_push_status(job_id: str, user_id: Optional[str] = None):
    """鏌ヨ閭鎺ㄩ€佷换鍔＄姸鎬?"""
    try:
        task = get_email_push_job(job_id)
        if user_id and task.get("status") != "not_found" and task.get("user_id") not in (None, user_id):
            task = {"status": "not_found", "job_id": job_id}
        return ResponseHelper.success(task, "鑾峰彇閭鎺ㄩ€佷换鍔＄姸鎬佹垚鍔?")
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)

@api_router.delete("/invoice/{user_id}/{invoice_id}", response_model=ApiResponse)
async def delete_invoice(user_id: str, invoice_id: str):
    """閸掔娀娅庨崣鎴犮偍閿涘牆鎮撻弮璺哄灩闂勩倖鏋冩禒璺烘嫲閺佺増宓佹惔鎾诡唶瑜版洩绱?"""
    try:
        result = file_service.delete_invoice(user_id, invoice_id)
        return ResponseHelper.success({"deleted": result}, "閸掔娀娅庨幋鎰")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


@api_router.post("/invoices/{user_id}/batch-delete", response_model=ApiResponse)
async def batch_delete_invoices(user_id: str, req: BatchDeleteRequest):
    """閹靛綊鍣洪崚鐘绘珟閸欐垹銈ㄩ敍鍫濇倱閺冭泛鍨归梽銈嗘瀮娴犺泛鎷伴弫鐗堝祦鎼存捁顔囪ぐ鏇礆"""
    try:
        result = file_service.batch_delete_invoices(user_id, req.invoice_ids)
        return ResponseHelper.success(result, "閹靛綊鍣洪崚鐘绘珟閹存劕濮?")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)


@api_router.get("/invoices/{user_id}/export")
async def export_invoices(user_id: str, keyword: Optional[str] = None):
    """鐎电厧鍤崣鎴犮偍Excel"""
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
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)

@api_router.get("/invoice/{user_id}/{invoice_id}", response_model=ApiResponse)
async def get_invoice_detail(user_id: str, invoice_id: str):
    """閼惧嘲褰囬崣鎴犮偍鐠囷附鍎?"""
    try:
        result = file_service.get_invoice_detail(user_id, invoice_id)
        return ResponseHelper.success(result, "閼惧嘲褰囬崣鎴犮偍鐠囷附鍎忛幋鎰")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)

# 绠＄悊鍛樼浉鍏宠矾鐢?
@api_router.get("/admin/users", response_model=ApiResponse)
async def get_all_users(page: int = 1, limit: int = 10):
    """閼惧嘲褰囬幍鈧張澶屾暏閹村嘲鍨悰顭掔礄缁狅紕鎮婇崨姗堢礆"""
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
        }, "閼惧嘲褰囬悽銊﹀煕閸掓銆冮幋鎰")
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)

@api_router.delete("/admin/user/{user_id}", response_model=ApiResponse)
async def delete_user(user_id: str):
    """鍒犻櫎鐢ㄦ埛锛堢鐞嗗憳锛?"""
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
        
        # 閸掔娀娅庨悽銊﹀煕鐠佹澘缍?
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        
        return ResponseHelper.success({"deleted": True}, "閸掔娀娅庨悽銊﹀煕閹存劕濮?")
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)

@api_router.get("/admin/invoices", response_model=ApiResponse)
async def get_all_invoices(page: int = 1, limit: int = 10, keyword: Optional[str] = None):
    """鑾峰彇鎵€鏈夊彂绁ㄥ垪琛紙绠＄悊鍛橈級"""
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
        
        # 鐠侊紕鐣婚幀缁樻殶
        total = len(all_invoices)
        
        # 閸掑棝銆?
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
        }, "閼惧嘲褰囬崣鎴犮偍閸掓銆冮幋鎰")
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)

@api_router.get("/admin/invoice-stats", response_model=ApiResponse)
async def get_admin_invoice_stats():
    """閼惧嘲褰囩粻锛勬倞閸涙绮虹拋鈥蹭繆閹?"""
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
                # 鏉╂柨娲?dict 妞嬪孩鐗哥悰宀嬬礉閺€顖涘瘮 row['count']
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
        
        return ResponseHelper.success(stats, "閼惧嘲褰囩紒鐔活吀娣団剝浼呴幋鎰")
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)

@api_router.get("/admin/stats", response_model=ApiResponse)
async def get_admin_stats():
    """閼惧嘲褰囩粻锛勬倞閸涙鎮ｉ崥鍫㈢埠鐠佲€蹭繆閹?"""
    try:
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 閻劍鍩涚紒鐔活吀
        cursor.execute("SELECT COUNT(*) as count FROM users")
        total_users = cursor.fetchone()['count']
        
        conn.close()
        
        # 閸欐垹銈ㄧ紒鐔活吀
        invoice_stats_result = await get_admin_invoice_stats()
        invoice_stats = invoice_stats_result.get('data', {})
        
        stats = {
            "total_users": total_users,
            **invoice_stats
        }
        
        return ResponseHelper.success(stats, "閼惧嘲褰囩紒鐔活吀娣団剝浼呴幋鎰")
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)

@api_router.get("/invoice/detail/{invoice_id}", response_model=ApiResponse)
async def get_invoice_detail_admin(invoice_id: str):
    """閼惧嘲褰囬崣鎴犮偍鐠囷附鍎忛敍鍫㈩吀閻炲棗鎲抽敍?"""
    try:
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 閺屻儴顕楅幍鈧張澶屾暏閹撮攱澹橀崚鎷岊嚉閸欐垹銈?
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
                    # 闂勫嫬濮為悽銊﹀煕ID閿涘本鏌熸笟鍨缁旑垱鐎柅鐘虫瀮娴犺泛婀撮崸鈧?
                    result["user_id"] = user_id
                    # 閺嬪嫰鈧娀顣╃憴鍫熸瀮娴犵ΚRL閿涘牅绱崗鍫滃▏閻劌顦╅悶鍡楁倵閻ㄥ嫬娴橀悧鍥风礆
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
                    return ResponseHelper.success(result, "閼惧嘲褰囬崣鎴犮偍鐠囷附鍎忛幋鎰")
                
                user_conn.close()
        
        conn.close()
        return ResponseHelper.error("閸欐垹銈ㄦ稉宥呯摠閸?", 404)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)

@api_router.delete("/invoice/{invoice_id}", response_model=ApiResponse)
async def delete_invoice_admin(invoice_id: str):
    """閸掔娀娅庨崣鎴犮偍閿涘牏顓搁悶鍡楁喅閿?"""
    try:
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 閺屻儴顕楅幍鈧張澶屾暏閹撮攱澹橀崚鎷岊嚉閸欐垹銈?
        cursor.execute("SELECT id FROM users")
        all_users = cursor.fetchall()
        
        deleted_count = 0
        for user in all_users:
            user_id = user['id']
            user_db_path = config.get_user_db_path(user_id)
            if os.path.exists(user_db_path):
                user_conn = sqlite3.connect(user_db_path)
                user_cursor = user_conn.cursor()
                
                # 閺屻儲澹橀崣鎴犮偍
                user_cursor.execute("SELECT * FROM invoice_details WHERE id = ?", (invoice_id,))
                invoice = user_cursor.fetchone()
                
                if invoice:
                    # 閸掔娀娅庨弬鍥︽
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
        
        return ResponseHelper.success({"deleted": deleted_count > 0}, "閸掔娀娅庨幋鎰")
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)

# OCR 閻╃鍙х捄顖滄暠
@api_router.post("/ocr/{user_id}/{invoice_id}", response_model=ApiResponse)
async def process_ocr(user_id: str, invoice_id: str):
    """閹靛濮╃憴锕€褰侽CR鐠囧棗鍩?"""
    try:
        # 閼惧嘲褰囬崣鎴犮偍娣団剝浼?
        invoice = file_service.get_invoice_detail(user_id, invoice_id)
        
        # 鏋勫缓鏂囦欢璺緞锛堜紭鍏堜娇鐢?processed 鍥剧墖锛?
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
            return ResponseHelper.error("閺傚洣娆㈡稉宥呯摠閸?", 404)
        
        # 閹笛嗩攽OCR鐠囧棗鍩?
        ocr_result = await ocr_service.process_invoice(file_path, file_extension)
        
        # 閺囧瓨鏌婄拠鍡楀焼缂佹挻鐏?
        success = await ocr_service.update_invoice_result(user_id, invoice_id, ocr_result)
        
        if success:
            return ResponseHelper.success(ocr_result, "OCR鐠囧棗鍩嗙€瑰本鍨?")
        else:
            return ResponseHelper.error("閺囧瓨鏌婄拠鍡楀焼缂佹挻鐏夋径杈Е", 500)
            
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)

# 缁崵绮洪惄绋垮彠鐠侯垳鏁?
@api_router.get("/health", response_model=ApiResponse)
async def health_check():
    """閸嬨儱鎮嶅Λ鈧弻?"""
    from datetime import datetime
    return ResponseHelper.success({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }, "缁崵绮烘潻鎰攽濮濓絽鐖?")

@api_router.get("/stats/{user_id}", response_model=ApiResponse)
async def get_user_stats(user_id: str):
    """閼惧嘲褰囬悽銊﹀煕缂佺喕顓告穱鈩冧紖"""
    try:
        # 閼惧嘲褰囬崣鎴犮偍缂佺喕顓?
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
        
        return ResponseHelper.success(stats, "閼惧嘲褰囩紒鐔活吀娣団剝浼呴幋鎰")
        
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"鍒犻櫎鐢ㄦ埛澶辫触: {str(e)}", 500)

# 瀵倹顒濷CR婢跺嫮鎮婇崙鑺ユ殶
async def process_ocr_async(user_id: str, invoice_id: str, file: UploadFile):
    """瀵倹顒炴径鍕倞OCR鐠囧棗鍩?"""
    try:
        from config import config
        import os
        
        # 缁涘绶熼弬鍥︽鐎瑰苯鍙忛崘娆忓弳
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
        
        # 閹笛嗩攽OCR鐠囧棗鍩?
        if os.path.exists(file_path):
            ocr_result = await ocr_service.process_invoice(file_path, file_extension)
            await ocr_service.update_invoice_result(user_id, invoice_id, ocr_result)
            print(f"OCR鐠囧棗鍩嗙€瑰本鍨? 閻劍鍩泏 {user_id}, 閸欐垹銈 {invoice_id}")
        
    except Exception as e:
        print(f"瀵倹顒濷CR婢跺嫮鎮婃径杈Е: {str(e)}")

# 鐎电厧鍙哸syncio
import asyncio






