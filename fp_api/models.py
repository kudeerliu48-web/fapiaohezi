from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any
from datetime import datetime

# 用户相关模型
class UserCreate(BaseModel):
    """用户创建模型"""
    username: str
    password: str
    email: EmailStr
    company: Optional[str] = None
    phone: Optional[str] = None

class UserLogin(BaseModel):
    """用户登录模型"""
    username: str
    password: str

class UserUpdate(BaseModel):
    """用户更新模型"""
    email: Optional[EmailStr] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None

class UserResponse(BaseModel):
    """用户响应模型"""
    id: str
    username: str
    email: str
    company: Optional[str]
    phone: Optional[str]
    status: int
    register_time: str
    last_login_time: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str = "user"

# 发票相关模型
class InvoiceDetail(BaseModel):
    """发票明细模型"""
    id: str
    filename: str
    invoice_amount: Optional[float] = None
    buyer: Optional[str] = None
    seller: Optional[str] = None
    invoice_number: Optional[str] = None
    recognition_status: int = 0  # 0:待识别 1:已识别 2:识别失败
    processing_time: Optional[float] = None
    ocr_text: Optional[str] = None
    json_info: Optional[dict] = None
    file_type: str
    file_size: int
    upload_time: str

class InvoiceCreate(BaseModel):
    """发票创建模型"""
    filename: str
    file_type: str
    file_size: int

class InvoiceUpdate(BaseModel):
    """发票更新模型"""
    invoice_amount: Optional[float] = None
    buyer: Optional[str] = None
    seller: Optional[str] = None
    invoice_number: Optional[str] = None
    recognition_status: Optional[int] = None
    processing_time: Optional[float] = None
    ocr_text: Optional[str] = None
    json_info: Optional[dict] = None

# OCR相关模型
class OCRRequest(BaseModel):
    """OCR请求模型"""
    file_path: str
    file_type: str

class OCRResponse(BaseModel):
    """OCR响应模型"""
    success: bool
    invoice_amount: Optional[float] = None
    buyer: Optional[str] = None
    seller: Optional[str] = None
    invoice_number: Optional[str] = None
    ocr_text: Optional[str] = None
    json_info: Optional[dict] = None
    processing_time: float
    error_message: Optional[str] = None

# 登录日志模型
class LoginLog(BaseModel):
    """登录日志模型"""
    id: str
    user_id: str
    login_time: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    login_status: int = 1

# 通用响应模型
class ApiResponse(BaseModel):
    """API 响应模型"""
    success: bool
    message: str
    data: Optional[Any] = None
    code: Optional[int] = None
    timestamp: str

class PaginatedResponse(BaseModel):
    """分页响应模型"""
    success: bool
    data: List[dict]
    pagination: dict
    timestamp: str

# 文件上传响应模型
class FileUploadResponse(BaseModel):
    """文件上传响应模型"""
    file_id: str
    filename: str
    file_size: int
    file_type: str
    upload_time: str
    status: str
    message: str


class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    invoice_ids: List[str]


class ExportInvoicesRequest(BaseModel):
    """导出发票请求（可选传入需要导出的发票ID列表）"""
    invoice_ids: Optional[List[str]] = None
    keyword: Optional[str] = None
