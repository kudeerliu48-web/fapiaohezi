from typing import Any, List, Optional

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    """注册请求（账号语义为手机号）。"""

    username: Optional[str] = None
    phone: Optional[str] = None
    password: str
    sms_code: Optional[str] = None
    email: Optional[EmailStr] = None
    company: Optional[str] = None


class UserLogin(BaseModel):
    """密码登录请求。"""

    username: Optional[str] = None
    phone: Optional[str] = None
    password: str


class UserLoginBySMS(BaseModel):
    """短信验证码登录请求。"""

    phone: str
    sms_code: str


class SmsCodeSendRequest(BaseModel):
    """发送短信验证码请求。"""

    phone: str
    purpose: str = "login"


class UserUpdate(BaseModel):
    """用户资料更新请求。"""

    username: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    company: Optional[str] = None
    avatar_url: Optional[str] = None


class UserResponse(BaseModel):
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


class InvoiceDetail(BaseModel):
    id: str
    filename: str
    invoice_amount: Optional[float] = None
    buyer: Optional[str] = None
    seller: Optional[str] = None
    invoice_number: Optional[str] = None
    recognition_status: int = 0
    processing_time: Optional[float] = None
    ocr_text: Optional[str] = None
    json_info: Optional[dict] = None
    file_type: str
    file_size: int
    upload_time: str


class InvoiceCreate(BaseModel):
    filename: str
    file_type: str
    file_size: int


class InvoiceUpdate(BaseModel):
    invoice_amount: Optional[float] = None
    buyer: Optional[str] = None
    seller: Optional[str] = None
    invoice_number: Optional[str] = None
    recognition_status: Optional[int] = None
    processing_time: Optional[float] = None
    ocr_text: Optional[str] = None
    json_info: Optional[dict] = None


class OCRRequest(BaseModel):
    file_path: str
    file_type: str


class OCRResponse(BaseModel):
    success: bool
    invoice_amount: Optional[float] = None
    buyer: Optional[str] = None
    seller: Optional[str] = None
    invoice_number: Optional[str] = None
    ocr_text: Optional[str] = None
    json_info: Optional[dict] = None
    processing_time: float
    error_message: Optional[str] = None


class LoginLog(BaseModel):
    id: str
    user_id: str
    login_time: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    login_status: int = 1


class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    code: Optional[int] = None
    timestamp: str


class PaginatedResponse(BaseModel):
    success: bool
    data: List[dict]
    pagination: dict
    timestamp: str


class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    file_size: int
    file_type: str
    upload_time: str
    status: str
    message: str


class BatchDeleteRequest(BaseModel):
    invoice_ids: List[str]


class ExportInvoicesRequest(BaseModel):
    invoice_ids: Optional[List[str]] = None
    keyword: Optional[str] = None
