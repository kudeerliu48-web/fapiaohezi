from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import Optional, List
import os
import sqlite3
import shutil

from models import (
    UserCreate, UserLogin, UserUpdate, UserResponse,
    InvoiceDetail, FileUploadResponse, ApiResponse, PaginatedResponse,
    BatchDeleteRequest
)
from services import user_service, file_service, ocr_service
from services import start_recognize_unrecognized, get_recognition_job
from utils import ResponseHelper
from database import DatabaseManager
from config import config
from workbench_service import workbench_service

from email_push import start_email_push_job, get_email_push_job

# 创建路由器
api_router = APIRouter(prefix="/api", tags=["API"])

# 用户相关路由
@api_router.post("/register", response_model=ApiResponse)
async def register(user: UserCreate):
    """用户注册"""
    try:
        from utils import hash_password
        user_data = user.dict()
        user_data['password'] = hash_password(user.password)
        
        result = user_service.register_user(user_data)
        return ResponseHelper.success(result, "注册成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"注册失败: {str(e)}", 500)

@api_router.post("/login", response_model=ApiResponse)
async def login(user: UserLogin):
    """用户登录"""
    try:
        result = user_service.login_user(user.username, user.password)
        return ResponseHelper.success(result, "登录成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"登录失败: {str(e)}", 500)

@api_router.get("/user/{user_id}", response_model=ApiResponse)
async def get_user(user_id: str):
    """获取用户信息"""
    try:
        user = user_service.get_user_info(user_id)
        return ResponseHelper.success(user, "获取用户信息成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"获取用户信息失败: {str(e)}", 500)

@api_router.put("/user/{user_id}", response_model=ApiResponse)
async def update_user(user_id: str, user_update: UserUpdate):
    """更新用户信息"""
    try:
        update_data = {k: v for k, v in user_update.dict().items() if v is not None}
        result = user_service.update_user_info(user_id, update_data)
        return ResponseHelper.success(result, "更新用户信息成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"更新用户信息失败: {str(e)}", 500)

# 文件相关路由
@api_router.post("/upload/{user_id}", response_model=ApiResponse)
async def upload_file(user_id: str, file: UploadFile = File(...)):
    """文件上传"""
    try:
        result = await file_service.upload_file(user_id, file)

        return ResponseHelper.success(result, "文件上传成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"文件上传失败: {str(e)}", 500)


# 工作台：上传并创建批次
@api_router.post("/workbench/batches/{user_id}/upload", response_model=ApiResponse)
async def wb_upload_batch(
    user_id: str,
    files: List[UploadFile] = File(...),
    remark: Optional[str] = Form(None),
):
    try:
        result = await workbench_service.upload_and_create_batch(user_id, files, remark)
        return ResponseHelper.success(result, "上传成功，批次已创建")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"上传失败: {str(e)}", 500)


@api_router.get("/workbench/batches/{user_id}", response_model=ApiResponse)
async def wb_get_batches(user_id: str, page: int = 1, limit: int = 10, status: Optional[str] = None):
    try:
        data = workbench_service.get_batches(user_id, page, limit, status)
        return ResponseHelper.success(data, "获取批次列表成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"获取批次列表失败: {str(e)}", 500)


@api_router.get("/workbench/batch/{user_id}/{batch_id}", response_model=ApiResponse)
async def wb_get_batch_detail(user_id: str, batch_id: str):
    try:
        data = workbench_service.get_batch_detail(user_id, batch_id)
        return ResponseHelper.success(data, "获取批次详情成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"获取批次详情失败: {str(e)}", 500)


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
        return ResponseHelper.success(data, "获取批次发票列表成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"获取批次发票列表失败: {str(e)}", 500)


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
        return ResponseHelper.success(data, "获取历史清单成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"获取历史清单失败: {str(e)}", 500)


@api_router.get("/workbench/invoice/{user_id}/{invoice_id}", response_model=ApiResponse)
async def wb_get_invoice_detail(user_id: str, invoice_id: str):
    try:
        data = workbench_service.get_invoice_detail(user_id, invoice_id)
        return ResponseHelper.success(data, "获取发票详情成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"获取发票详情失败: {str(e)}", 500)


@api_router.get("/workbench/invoice/{user_id}/{invoice_id}/steps", response_model=ApiResponse)
async def wb_get_invoice_steps(user_id: str, invoice_id: str):
    try:
        data = workbench_service.get_invoice_steps(user_id, invoice_id)
        return ResponseHelper.success(data, "获取处理步骤成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"获取处理步骤失败: {str(e)}", 500)


@api_router.post("/workbench/invoice/{user_id}/{invoice_id}/retry", response_model=ApiResponse)
async def wb_retry_invoice(user_id: str, invoice_id: str):
    try:
        data = await workbench_service.rerun_invoice(user_id, invoice_id)
        return ResponseHelper.success(data, "重试识别成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"重试识别失败: {str(e)}", 500)


@api_router.post("/workbench/batch/{user_id}/{batch_id}/retry", response_model=ApiResponse)
async def wb_retry_batch(user_id: str, batch_id: str):
    try:
        data = await workbench_service.rerun_batch(user_id, batch_id)
        return ResponseHelper.success(data, "批次重试识别完成")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"批次重试识别失败: {str(e)}", 500)


@api_router.delete("/workbench/invoice/{user_id}/{invoice_id}", response_model=ApiResponse)
async def wb_delete_invoice(user_id: str, invoice_id: str):
    try:
        data = workbench_service.delete_invoice(user_id, invoice_id)
        return ResponseHelper.success(data, "删除发票成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除发票失败: {str(e)}", 500)


@api_router.delete("/workbench/batch/{user_id}/{batch_id}", response_model=ApiResponse)
async def wb_delete_batch(user_id: str, batch_id: str):
    try:
        data = workbench_service.delete_batch(user_id, batch_id)
        return ResponseHelper.success(data, "删除批次成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除批次失败: {str(e)}", 500)


@api_router.delete("/workbench/history/{user_id}/all", response_model=ApiResponse)
async def wb_clear_history(user_id: str):
    try:
        data = workbench_service.clear_all_history(user_id)
        return ResponseHelper.success(data, "历史记录已清空")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"清空历史失败: {str(e)}", 500)


@api_router.get("/workbench/overview/{user_id}", response_model=ApiResponse)
async def wb_overview(user_id: str):
    try:
        data = workbench_service.get_overview_stats(user_id)
        return ResponseHelper.success(data, "获取总览统计成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"获取总览统计失败: {str(e)}", 500)


@api_router.post("/recognize/{user_id}/unrecognized", response_model=ApiResponse)
async def recognize_unrecognized(user_id: str):
    """提交所有未识别的发票（recognition_status=0）进行识别"""
    try:
        job_id = start_recognize_unrecognized(user_id)
        return ResponseHelper.success({"job_id": job_id}, "识别任务已开始")
    except Exception as e:
        return ResponseHelper.error(f"启动识别任务失败: {str(e)}", 500)


@api_router.get("/recognize/status/{job_id}", response_model=ApiResponse)
async def recognize_status(job_id: str):
    """查询识别任务状态"""
    try:
        return ResponseHelper.success(get_recognition_job(job_id), "获取识别任务状态成功")
    except Exception as e:
        return ResponseHelper.error(f"获取识别任务状态失败: {str(e)}", 500)

@api_router.get("/invoices/{user_id}", response_model=ApiResponse)
async def get_invoices(user_id: str, page: int = 1, limit: int = 10, keyword: Optional[str] = None, recognized_only: bool = False):
    """获取用户发票列表"""
    try:
        result = file_service.get_user_invoices(user_id, page, limit, keyword, recognized_only)
        return ResponseHelper.success(result, "获取发票列表成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"获取发票列表失败: {str(e)}", 500)


@api_router.post("/email-push/{user_id}/start", response_model=ApiResponse)
async def start_email_push(
    user_id: str,
    range_key: str = Form(...),
    mailbox: Optional[str] = Form(None),
    auth_code: str = Form(...),
):
    """邮箱推送：拉取邮件发票附件并入库"""
    try:
        print(f"[DEBUG] Received range_key: {range_key}")  # Debug log
        # range_key: 7d | 1m | 3m | 6m | 12m
        range_days_map = {
            "7d": 7,
            "1m": 30,
            "3m": 90,
            "6m": 180,
            "12m": 365,
        }
        days = range_days_map.get(range_key)
        if not days:
            return ResponseHelper.error(f"不支持的时间范围: {range_key}", 400)

        user = user_service.get_user_info(user_id)
        resolved_mailbox = (mailbox or user.get("email") or "").strip()
        if not resolved_mailbox:
            return ResponseHelper.error("邮箱不能为空", 400)
        if not auth_code:
            return ResponseHelper.error("授权码不能为空", 400)

        job_id = start_email_push_job(user_id=user_id, mailbox=resolved_mailbox, auth_code=auth_code, days=days)
        return ResponseHelper.success({"job_id": job_id}, "邮箱推送任务已开始")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"启动邮箱推送失败: {str(e)}", 500)


@api_router.get("/email-push/status/{job_id}", response_model=ApiResponse)
async def get_email_push_status(job_id: str):
    """查询邮箱推送任务状态"""
    try:
        return ResponseHelper.success(get_email_push_job(job_id), "获取邮箱推送任务状态成功")
    except Exception as e:
        return ResponseHelper.error(f"获取邮箱推送任务状态失败: {str(e)}", 500)


@api_router.delete("/invoice/{user_id}/{invoice_id}", response_model=ApiResponse)
async def delete_invoice(user_id: str, invoice_id: str):
    """删除发票（同时删除文件和数据库记录）"""
    try:
        result = file_service.delete_invoice(user_id, invoice_id)
        return ResponseHelper.success({"deleted": result}, "删除成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"删除失败: {str(e)}", 500)


@api_router.post("/invoices/{user_id}/batch-delete", response_model=ApiResponse)
async def batch_delete_invoices(user_id: str, req: BatchDeleteRequest):
    """批量删除发票（同时删除文件和数据库记录）"""
    try:
        result = file_service.batch_delete_invoices(user_id, req.invoice_ids)
        return ResponseHelper.success(result, "批量删除成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"批量删除失败: {str(e)}", 500)


@api_router.get("/invoices/{user_id}/export")
async def export_invoices(user_id: str, keyword: Optional[str] = None):
    """导出发票Excel"""
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
        return ResponseHelper.error(f"导出失败: {str(e)}", 500)

@api_router.get("/invoice/{user_id}/{invoice_id}", response_model=ApiResponse)
async def get_invoice_detail(user_id: str, invoice_id: str):
    """获取发票详情"""
    try:
        result = file_service.get_invoice_detail(user_id, invoice_id)
        return ResponseHelper.success(result, "获取发票详情成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"获取发票详情失败: {str(e)}", 500)

# 管理员相关路由
@api_router.get("/admin/users", response_model=ApiResponse)
async def get_all_users(page: int = 1, limit: int = 10):
    """获取所有用户列表（管理员）"""
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
        }, "获取用户列表成功")
    except Exception as e:
        return ResponseHelper.error(f"获取用户列表失败：{str(e)}", 500)

@api_router.delete("/admin/user/{user_id}", response_model=ApiResponse)
async def delete_user(user_id: str):
    """删除用户（管理员）"""
    try:
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 删除用户数据库
        user_db_path = config.get_user_db_path(user_id)
        if os.path.exists(user_db_path):
            os.remove(user_db_path)
        
        # 删除用户文件夹
        user_dir = config.get_user_dir(user_id)
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)
        
        # 删除用户记录
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        
        return ResponseHelper.success({"deleted": True}, "删除用户成功")
    except Exception as e:
        return ResponseHelper.error(f"删除用户失败：{str(e)}", 500)

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
        
        # 查询所有用户的发票（需要遍历所有用户数据库）
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
        
        # 计算总数
        total = len(all_invoices)
        
        # 分页
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
        }, "获取发票列表成功")
    except Exception as e:
        return ResponseHelper.error(f"获取发票列表失败：{str(e)}", 500)

@api_router.get("/admin/invoice-stats", response_model=ApiResponse)
async def get_admin_invoice_stats():
    """获取管理员统计信息"""
    try:
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 查询所有用户
        cursor.execute("SELECT id FROM users")
        all_users = cursor.fetchall()
        
        total_invoices = 0
        recognized_invoices = 0
        total_amount = 0.0
        
        # 统计每个用户的发票
        for user in all_users:
            user_id = user['id']
            user_db_path = config.get_user_db_path(user_id)
            if os.path.exists(user_db_path):
                user_conn = sqlite3.connect(user_db_path)
                # 返回 dict 风格行，支持 row['count']
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
        
        return ResponseHelper.success(stats, "获取统计信息成功")
    except Exception as e:
        return ResponseHelper.error(f"获取统计信息失败：{str(e)}", 500)

@api_router.get("/admin/stats", response_model=ApiResponse)
async def get_admin_stats():
    """获取管理员综合统计信息"""
    try:
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 用户统计
        cursor.execute("SELECT COUNT(*) as count FROM users")
        total_users = cursor.fetchone()['count']
        
        conn.close()
        
        # 发票统计
        invoice_stats_result = await get_admin_invoice_stats()
        invoice_stats = invoice_stats_result.get('data', {})
        
        stats = {
            "total_users": total_users,
            **invoice_stats
        }
        
        return ResponseHelper.success(stats, "获取统计信息成功")
    except Exception as e:
        return ResponseHelper.error(f"获取统计信息失败：{str(e)}", 500)

@api_router.get("/invoice/detail/{invoice_id}", response_model=ApiResponse)
async def get_invoice_detail_admin(invoice_id: str):
    """获取发票详情（管理员）"""
    try:
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 查询所有用户找到该发票
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
                    # 附加用户ID，方便前端构造文件地址
                    result["user_id"] = user_id
                    # 构造预览文件URL（优先使用处理后的图片）
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
                    return ResponseHelper.success(result, "获取发票详情成功")
                
                user_conn.close()
        
        conn.close()
        return ResponseHelper.error("发票不存在", 404)
    except Exception as e:
        return ResponseHelper.error(f"获取发票详情失败：{str(e)}", 500)

@api_router.delete("/invoice/{invoice_id}", response_model=ApiResponse)
async def delete_invoice_admin(invoice_id: str):
    """删除发票（管理员）"""
    try:
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 查询所有用户找到该发票
        cursor.execute("SELECT id FROM users")
        all_users = cursor.fetchall()
        
        deleted_count = 0
        for user in all_users:
            user_id = user['id']
            user_db_path = config.get_user_db_path(user_id)
            if os.path.exists(user_db_path):
                user_conn = sqlite3.connect(user_db_path)
                user_cursor = user_conn.cursor()
                
                # 查找发票
                user_cursor.execute("SELECT * FROM invoice_details WHERE id = ?", (invoice_id,))
                invoice = user_cursor.fetchone()
                
                if invoice:
                    # 删除文件
                    if invoice.get('saved_filename'):
                        saved_path = os.path.join(config.get_upload_dir(user_id), invoice['saved_filename'])
                        if os.path.exists(saved_path):
                            os.remove(saved_path)
                    
                    if invoice.get('processed_filename'):
                        processed_path = os.path.join(config.get_processed_dir(user_id), invoice['processed_filename'])
                        if os.path.exists(processed_path):
                            os.remove(processed_path)
                    
                    # 删除数据库记录
                    user_cursor.execute("DELETE FROM invoice_details WHERE id = ?", (invoice_id,))
                    user_conn.commit()
                    deleted_count += 1
                
                user_conn.close()
        
        conn.close()
        
        return ResponseHelper.success({"deleted": deleted_count > 0}, "删除成功")
    except Exception as e:
        return ResponseHelper.error(f"删除失败：{str(e)}", 500)

# OCR 相关路由
@api_router.post("/ocr/{user_id}/{invoice_id}", response_model=ApiResponse)
async def process_ocr(user_id: str, invoice_id: str):
    """手动触发OCR识别"""
    try:
        # 获取发票信息
        invoice = file_service.get_invoice_detail(user_id, invoice_id)
        
        # 构建文件路径（优先使用 processed 图片）
        from config import config
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
            return ResponseHelper.error("文件不存在", 404)
        
        # 执行OCR识别
        ocr_result = await ocr_service.process_invoice(file_path, file_extension)
        
        # 更新识别结果
        success = await ocr_service.update_invoice_result(user_id, invoice_id, ocr_result)
        
        if success:
            return ResponseHelper.success(ocr_result, "OCR识别完成")
        else:
            return ResponseHelper.error("更新识别结果失败", 500)
            
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"OCR识别失败: {str(e)}", 500)

# 系统相关路由
@api_router.get("/health", response_model=ApiResponse)
async def health_check():
    """健康检查"""
    from datetime import datetime
    return ResponseHelper.success({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }, "系统运行正常")

@api_router.get("/stats/{user_id}", response_model=ApiResponse)
async def get_user_stats(user_id: str):
    """获取用户统计信息"""
    try:
        # 获取发票统计
        invoices_result = file_service.get_user_invoices(user_id, 1, 1000)
        invoices = invoices_result.get('invoices', [])
        
        total_count = len(invoices)
        recognized_count = len([inv for inv in invoices if inv['recognition_status'] == 1])
        pending_count = len([inv for inv in invoices if inv['recognition_status'] == 0])
        failed_count = len([inv for inv in invoices if inv['recognition_status'] == 2])
        
        # 计算总金额
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
        
        return ResponseHelper.success(stats, "获取统计信息成功")
        
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"获取统计信息失败: {str(e)}", 500)

# 异步OCR处理函数
async def process_ocr_async(user_id: str, invoice_id: str, file: UploadFile):
    """异步处理OCR识别"""
    try:
        from config import config
        import os
        
        # 等待文件完全写入
        await asyncio.sleep(1)
        
        # 构建文件路径（优先从数据库取 processed_filename）
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
        
        # 执行OCR识别
        if os.path.exists(file_path):
            ocr_result = await ocr_service.process_invoice(file_path, file_extension)
            await ocr_service.update_invoice_result(user_id, invoice_id, ocr_result)
            print(f"OCR识别完成: 用户{user_id}, 发票{invoice_id}")
        
    except Exception as e:
        print(f"异步OCR处理失败: {str(e)}")

# 导入asyncio
import asyncio
