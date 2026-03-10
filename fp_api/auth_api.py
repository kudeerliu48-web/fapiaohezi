"""认证模块：注册 / 登录 / SMS / 用户信息。"""

import random
import re
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from config import config
from database import DatabaseManager, UserDatabaseManager
from models import (
    ApiResponse,
    SmsCodeSendRequest,
    UserCreate,
    UserLogin,
    UserLoginBySMS,
    UserUpdate,
)
from response import ResponseHelper
from utils import (
    create_user_folders,
    generate_uuid,
    hash_password,
    init_user_database,
    verify_password,
)

auth_router = APIRouter(prefix="/api", tags=["Auth"])

# ── 模块级状态 ──────────────────────────────────────────────
_main_db = DatabaseManager()

PHONE_PATTERN = re.compile(r"^1\d{10}$")

# SMS 验证码存储
_sms_codes: Dict[str, dict] = {}
_sms_lock = threading.Lock()


# ── SMS 辅助函数 ────────────────────────────────────────────

def _sms_cache_key(phone: str, purpose: str) -> str:
    return f"{purpose}:{phone}"


def _send_sms_code(phone: str, purpose: str = "login") -> dict:
    phone = (phone or "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail="手机号不能为空")

    code = f"{random.randint(0, 999999):06d}"
    expire_at = datetime.now() + timedelta(seconds=config.SMS_CODE_EXPIRE_SECONDS)
    key = _sms_cache_key(phone, purpose)

    with _sms_lock:
        _sms_codes[key] = {
            "code": code,
            "expire_at": expire_at,
            "updated_at": datetime.now().isoformat(),
        }

    if not config.SMS_MOCK_MODE:
        _send_aliyun_sms(phone, code)

    payload: Dict[str, Any] = {
        "phone": phone,
        "purpose": purpose,
        "expire_seconds": config.SMS_CODE_EXPIRE_SECONDS,
        "sent_at": datetime.now().isoformat(),
    }
    if config.SMS_MOCK_MODE:
        payload["debug_code"] = code
    return payload


def _verify_sms_code(phone: str, code: str, purpose: str = "login", consume: bool = True) -> bool:
    phone = (phone or "").strip()
    key = _sms_cache_key(phone, purpose)

    with _sms_lock:
        record = _sms_codes.get(key)
        if not record:
            return False
        if datetime.now() > record["expire_at"]:
            _sms_codes.pop(key, None)
            return False
        if str(record["code"]) != str(code or ""):
            return False
        if consume:
            _sms_codes.pop(key, None)
        return True


def _send_aliyun_sms(phone: str, code: str) -> None:
    """预留阿里云短信发送调用点。"""
    if not all([
        config.ALIYUN_SMS_ACCESS_KEY_ID,
        config.ALIYUN_SMS_ACCESS_KEY_SECRET,
        config.ALIYUN_SMS_SIGN_NAME,
        config.ALIYUN_SMS_TEMPLATE_CODE,
    ]):
        raise HTTPException(status_code=500, detail="阿里云短信配置缺失")
    return


# ── 公共工具 ────────────────────────────────────────────────

def _resolve_phone_value(username: Optional[str], phone: Optional[str]) -> str:
    resolved = (phone or username or "").strip()
    if not resolved:
        raise HTTPException(status_code=400, detail="手机号不能为空")
    if not PHONE_PATTERN.match(resolved):
        raise HTTPException(status_code=400, detail="手机号格式不正确")
    return resolved


# ── 端点 ────────────────────────────────────────────────────

@auth_router.post("/auth/register", response_model=ApiResponse)
@auth_router.post("/register", response_model=ApiResponse)
async def register(user: UserCreate):
    """注册（手机号作为账号）。"""
    try:
        phone = _resolve_phone_value(user.username, user.phone)
        if len((user.password or "")) < 6:
            return ResponseHelper.error("密码长度不能少于6位", 400)

        sms_code = (user.sms_code or "").strip()
        if sms_code and not _verify_sms_code(phone, sms_code, purpose="register", consume=True):
            return ResponseHelper.error("验证码错误或已过期", 400)

        if _main_db.user_exists(username=phone):
            raise HTTPException(status_code=400, detail="手机号已存在")

        email = (user.email or "").strip() or f"{phone}@placeholder.local"
        existing_email_user = _main_db.get_user_by_email(email)
        if existing_email_user:
            raise HTTPException(status_code=400, detail="邮箱已存在")

        user_data = {
            "username": phone,
            "phone": phone,
            "password": hash_password(user.password),
            "email": email,
            "company": user.company or None,
        }
        user_id = _main_db.create_user(user_data)

        create_user_folders(user_id)
        user_db_path = config.get_user_db_path(user_id)
        init_user_database(user_id, user_db_path)

        return ResponseHelper.success({"user_id": user_id, "message": "注册成功"}, "注册成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"注册失败: {str(e)}", 500)


@auth_router.post("/auth/login-by-password", response_model=ApiResponse)
@auth_router.post("/login", response_model=ApiResponse)
async def login(user: UserLogin):
    """手机号+密码登录。"""
    try:
        phone = _resolve_phone_value(user.username, user.phone)
        db_user = _main_db.get_user_by_username(phone)
        if not db_user or not verify_password(user.password, db_user["password"]):
            if db_user:
                _main_db.create_login_log(db_user["id"], None, None, 0)
            raise HTTPException(status_code=401, detail="手机号或密码错误")

        _main_db.update_login_time(db_user["id"])
        _main_db.create_login_log(db_user["id"], None, None, 1)

        user_info = {
            "id": db_user["id"],
            "username": db_user["username"],
            "email": db_user["email"],
            "company": db_user["company"],
            "phone": db_user.get("phone") or db_user["username"],
            "status": db_user["status"],
            "role": db_user["role"],
        }
        return ResponseHelper.success({"message": "登录成功", "user": user_info}, "登录成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"登录失败: {str(e)}", 500)


@auth_router.post("/auth/send-sms-code", response_model=ApiResponse)
async def send_sms_code(payload: SmsCodeSendRequest):
    """发送短信验证码（阿里云接口预留）。"""
    try:
        phone = _resolve_phone_value(payload.phone, payload.phone)
        purpose = (payload.purpose or "login").strip() or "login"
        if purpose not in {"login", "register"}:
            purpose = "login"
        data = _send_sms_code(phone, purpose=purpose)
        return ResponseHelper.success(data, "验证码已发送")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"发送验证码失败: {str(e)}", 500)


@auth_router.post("/auth/login-by-sms", response_model=ApiResponse)
async def login_by_sms(payload: UserLoginBySMS):
    """手机号+验证码登录。"""
    try:
        phone = _resolve_phone_value(payload.phone, payload.phone)
        if not _verify_sms_code(phone, payload.sms_code, purpose="login", consume=True):
            return ResponseHelper.error("验证码错误或已过期", 400)

        user = _main_db.get_user_by_username(phone)
        if not user:
            return ResponseHelper.error("手机号未注册", 404)

        _main_db.update_login_time(user["id"])
        _main_db.create_login_log(user["id"], None, "sms", 1)

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


@auth_router.get("/user/{user_id}", response_model=ApiResponse)
async def get_user(user_id: str):
    """获取用户信息。"""
    try:
        user = _main_db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        user["phone"] = user.get("phone") or user.get("username")
        return ResponseHelper.success(user, "获取用户信息成功")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"获取用户信息失败: {str(e)}", 500)


@auth_router.put("/user/{user_id}", response_model=ApiResponse)
async def update_user(user_id: str, user_update: UserUpdate):
    """更新用户信息。"""
    try:
        user = _main_db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        update_data = {k: v for k, v in user_update.dict().items() if v is not None}

        if "email" in update_data:
            email_value = (update_data.get("email") or "").strip()
            if not email_value:
                update_data.pop("email", None)
            else:
                existing_user = _main_db.get_user_by_email(email_value)
                if existing_user and existing_user["id"] != user_id:
                    raise HTTPException(status_code=400, detail="邮箱已存在")

        if "phone" in update_data:
            phone = (update_data.get("phone") or "").strip()
            if not phone:
                update_data.pop("phone", None)
            else:
                if not PHONE_PATTERN.match(phone):
                    raise HTTPException(status_code=400, detail="手机号格式不正确")
                existing_phone_user = _main_db.get_user_by_username(phone)
                if existing_phone_user and existing_phone_user["id"] != user_id:
                    raise HTTPException(status_code=400, detail="手机号已存在")
                update_data["username"] = phone

        success = _main_db.update_user(user_id, update_data)
        if success:
            return ResponseHelper.success({"message": "用户信息更新成功"}, "更新用户信息成功")
        raise HTTPException(status_code=400, detail="没有可更新的字段")
    except HTTPException as e:
        return ResponseHelper.error(e.detail, e.status_code)
    except Exception as e:
        return ResponseHelper.error(f"更新用户信息失败: {str(e)}", 500)
