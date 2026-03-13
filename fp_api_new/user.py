import os
import re
import sqlite3
import threading
import random
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, Tuple

from utils import generate_uuid, hash_password, verify_password, format_datetime, create_user_folders, ResponseHelper
from config import config

router = APIRouter(prefix="/api", tags=["用户管理"])

PHONE_PATTERN = re.compile(r"^1\d{10}$")

_sms_codes: Dict[str, Dict[str, Any]] = {}
_sms_codes_lock = threading.Lock()


class UserCreate(BaseModel):
    username: Optional[str] = None
    phone: Optional[str] = None
    password: str
    email: Optional[EmailStr] = None
    company: Optional[str] = None
    sms_code: Optional[str] = None


class UserLogin(BaseModel):
    username: Optional[str] = None
    phone: Optional[str] = None
    password: str


class UserLoginBySMS(BaseModel):
    phone: str
    sms_code: str


class SmsCodeSendRequest(BaseModel):
    phone: str
    purpose: str = "login"


class UserUpdate(BaseModel):
    username: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    company: Optional[str] = None
    avatar_url: Optional[str] = None


def get_main_db_connection():
    conn = sqlite3.connect("main.db")
    conn.row_factory = sqlite3.Row
    return conn


# 识别额度：普通用户 10 次；免费用户仅受期限限制（不限次数）；月付/年付不限
RECOGNITION_QUOTA_NORMAL = 10


def check_recognition_quota(user_id: str, add_count: int = 0) -> Tuple[bool, str]:
    """
    检查用户是否可继续使用识别：会员未到期且未超额度。
    返回 (是否允许, 不允许时的提示文案)。
    """
    conn = get_main_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT member_type, member_end_at, recognition_used FROM users WHERE id = ?""",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return False, "用户不存在"
    r = dict(row)
    member_type = (r.get("member_type") or "normal").strip() or "normal"
    member_end_at = r.get("member_end_at")
    recognition_used = int(r.get("recognition_used") or 0)

    # 免费用户：检查是否到期
    if member_type == "free":
        if member_end_at:
            try:
                end_str = str(member_end_at).replace("T", " ").strip()[:19]
                end_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
                if datetime.now() >= end_dt:
                    return False, "免费会员已到期，请升级为付费会员后再使用识别功能"
            except Exception:
                return False, "会员已到期，请续费后再使用识别功能"
        else:
            return False, "会员已到期，请续费后再使用识别功能"
        # 免费用户：未到期则不限次数
        return True, ""

    # 月付/年付：不限次数
    if member_type in ("monthly", "yearly"):
        return True, ""

    # 普通用户：检查额度
    quota = RECOGNITION_QUOTA_NORMAL
    if recognition_used + add_count > quota:
        return False, f"识别次数已用完（已用 {recognition_used}/{quota} 次），请升级会员或联系管理员"
    return True, ""


def init_main_database():
    conn = get_main_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT UNIQUE,
            company TEXT,
            phone TEXT,
            login_time TEXT,
            status INTEGER DEFAULT 1,
            register_time TEXT NOT NULL,
            last_login_time TEXT,
            avatar_url TEXT,
            role TEXT DEFAULT 'user',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            field1 TEXT,
            field2 TEXT,
            field3 TEXT,
            member_type TEXT DEFAULT 'normal',
            member_start_at TEXT,
            member_end_at TEXT,
            recognition_used INTEGER DEFAULT 0
        )
    ''')
    try:
        cursor.execute("PRAGMA table_info(users)")
        cols = [r[1] for r in cursor.fetchall()]
        if "member_type" not in cols:
            cursor.execute("ALTER TABLE users ADD COLUMN member_type TEXT DEFAULT 'normal'")
        if "member_start_at" not in cols:
            cursor.execute("ALTER TABLE users ADD COLUMN member_start_at TEXT")
        if "member_end_at" not in cols:
            cursor.execute("ALTER TABLE users ADD COLUMN member_end_at TEXT")
        if "recognition_used" not in cols:
            cursor.execute("ALTER TABLE users ADD COLUMN recognition_used INTEGER DEFAULT 0")
    except Exception:
        pass
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS login_logs (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            login_time TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            login_status INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_sync (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            invoice_id TEXT NOT NULL,
            batch_id TEXT,
            invoice_number TEXT,
            invoice_date TEXT,
            invoice_amount REAL,
            total_with_tax REAL,
            buyer TEXT,
            seller TEXT,
            recognition_status INTEGER DEFAULT 0,
            processing_time REAL,
            upload_time TEXT,
            file_type TEXT,
            file_size INTEGER,
            ocr_text TEXT,
            filename TEXT,
            saved_filename TEXT,
            updated_at TEXT,
            created_at TEXT,
            UNIQUE(user_id, invoice_id)
        )
    ''')
    conn.commit()
    conn.close()


init_main_database()


def _resolve_phone_value(username: Optional[str], phone: Optional[str]) -> str:
    resolved = (phone or username or "").strip()
    if not resolved:
        raise HTTPException(status_code=400, detail="手机号不能为空")
    if not PHONE_PATTERN.match(resolved):
        raise HTTPException(status_code=400, detail="手机号格式不正确")
    return resolved


def _send_mock_sms_code(phone: str, purpose: str) -> Dict[str, Any]:
    code = "".join(random.choices("0123456789", k=6))
    with _sms_codes_lock:
        _sms_codes[f"{phone}_{purpose}"] = {
            "code": code,
            "expires_at": format_datetime(),
            "purpose": purpose
        }
    return {
        "success": True,
        "message": "验证码已发送（模拟模式）",
        "mock_code": code
    }


def _verify_sms_code(phone: str, code: str, purpose: str, consume: bool = True) -> bool:
    key = f"{phone}_{purpose}"
    with _sms_codes_lock:
        data = _sms_codes.get(key)
        if not data:
            return False
        if data["code"] != code:
            return False
        if consume:
            del _sms_codes[key]
    return True


@router.post("/auth/register")
async def auth_register(user: UserCreate):
    phone = _resolve_phone_value(user.username, user.phone)
    if len((user.password or "")) < 6:
        return ResponseHelper.error("密码长度不能少于6位", 400)

    conn = get_main_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE username = ?", (phone,))
    if cursor.fetchone():
        conn.close()
        return ResponseHelper.error("手机号已存在", 400)

    user_id = generate_uuid()
    current_time = format_datetime()
    hashed_password = hash_password(user.password)

    cursor.execute('''
        INSERT INTO users (
            id, username, password, company, phone,
            register_time, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id, phone, hashed_password, user.company, phone,
        current_time, 1, current_time, current_time
    ))
    conn.commit()
    conn.close()

    create_user_folders(user_id)

    return ResponseHelper.success({
        "user_id": user_id,
        "username": phone,
        "message": "注册成功"
    }, "注册成功")


@router.post("/auth/login-by-password")
async def auth_login_by_password(user: UserLogin):
    try:
        print("=" * 50)
        print("[DEBUG] === 登录请求开始 ===")
        print(f"[DEBUG] 请求数据：username={user.username}, phone={user.phone}")
        
        phone = _resolve_phone_value(user.username, user.phone)
        print(f"[DEBUG] 解析后的手机号：{phone}")

        conn = get_main_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, username, password, email, company, phone, status, role
            FROM users WHERE username = ?
        ''', (phone,))
        db_user = cursor.fetchone()
        print(f"[DEBUG] 数据库查询结果：{db_user is not None}")

        if not db_user:
            print(f"[DEBUG] 用户不存在：{phone}")
            conn.close()
            return ResponseHelper.error("手机号或密码错误", 401)
        
        print(f"[DEBUG] 验证密码...")
        print(f"[DEBUG] 输入密码：{user.password}")
        print(f"[DEBUG] 数据库密码哈希：{db_user['password']}")
        
        password_valid = verify_password(user.password, db_user["password"])
        print(f"[DEBUG] 密码验证结果：{password_valid}")

        if not password_valid:
            print(f"[DEBUG] 密码错误")
            conn.close()
            return ResponseHelper.error("手机号或密码错误", 401)

        print(f"[DEBUG] 密码验证通过，更新登录时间...")
        current_time = format_datetime()
        cursor.execute(
            "UPDATE users SET login_time = ?, last_login_time = ? WHERE id = ?",
            (current_time, current_time, db_user["id"])
        )

        log_id = generate_uuid()
        cursor.execute('''
            INSERT INTO login_logs (id, user_id, login_time, login_status)
            VALUES (?, ?, ?, 1)
        ''', (log_id, db_user["id"], current_time))

        conn.commit()
        conn.close()
        print(f"[DEBUG] 数据库更新成功")

        user_info = {
            "id": db_user["id"],
            "username": db_user["username"],
            "email": db_user["email"],
            "company": db_user["company"],
            "phone": db_user["phone"] if db_user["phone"] else db_user["username"],
            "status": db_user["status"],
            "role": db_user["role"],
        }
        
        print(f"[DEBUG] 登录成功，用户信息：{user_info}")
        print("[DEBUG] === 登录流程结束 ===")
        print("=" * 50)

        return ResponseHelper.success({
            "message": "登录成功",
            "user": user_info
        }, "登录成功")
        
    except Exception as e:
        import traceback
        print("=" * 50)
        print(f"[ERROR] 登录失败：{str(e)}")
        print(f"[ERROR] 错误堆栈：{traceback.format_exc()}")
        print("=" * 50)
        return ResponseHelper.error(f"服务器内部错误：{str(e)}", 500)


@router.post("/auth/send-sms-code")
async def auth_send_sms_code(payload: SmsCodeSendRequest):
    phone = payload.phone.strip()
    if not PHONE_PATTERN.match(phone):
        return ResponseHelper.error("手机号格式不正确", 400)

    purpose = (payload.purpose or "login").strip()
    if purpose not in {"login", "register"}:
        purpose = "login"

    if config.SMS_MOCK_MODE:
        result = _send_mock_sms_code(phone, purpose)
        return ResponseHelper.success(result, "验证码已发送")

    return ResponseHelper.error("短信服务未配置", 500)


@router.post("/auth/login-by-sms")
async def auth_login_by_sms(payload: UserLoginBySMS):
    phone = payload.phone.strip()
    if not PHONE_PATTERN.match(phone):
        return ResponseHelper.error("手机号格式不正确", 400)

    if not _verify_sms_code(phone, payload.sms_code, purpose="login", consume=True):
        return ResponseHelper.error("验证码错误或已过期", 400)

    conn = get_main_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, username, email, company, phone, status, role
        FROM users WHERE username = ?
    ''', (phone,))
    db_user = cursor.fetchone()

    if not db_user:
        conn.close()
        return ResponseHelper.error("手机号未注册", 404)

    current_time = format_datetime()
    cursor.execute(
        "UPDATE users SET login_time = ?, last_login_time = ? WHERE id = ?",
        (current_time, current_time, db_user["id"])
    )

    log_id = generate_uuid()
    cursor.execute('''
        INSERT INTO login_logs (id, user_id, login_time, login_status)
        VALUES (?, ?, ?, 1)
    ''', (log_id, db_user["id"], current_time))

    conn.commit()
    conn.close()

    user_info = {
        "id": db_user["id"],
        "username": db_user["username"],
        "email": db_user["email"],
        "company": db_user["company"],
        "phone": db_user["phone"] if db_user["phone"] else db_user["username"],
        "status": db_user["status"],
        "role": db_user["role"],
    }

    return ResponseHelper.success({
        "message": "登录成功",
        "user": user_info
    }, "登录成功")


@router.post("/user")
async def create_user(user: UserCreate):
    phone = _resolve_phone_value(user.username, user.phone)
    if len((user.password or "")) < 6:
        return ResponseHelper.error("密码长度不能少于6位", 400)

    conn = get_main_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE username = ?", (phone,))
    if cursor.fetchone():
        conn.close()
        return ResponseHelper.error("手机号已存在", 400)

    email = (user.email or "").strip() or f"{phone}@placeholder.local"
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        conn.close()
        return ResponseHelper.error("邮箱已存在", 400)

    user_id = generate_uuid()
    current_time = format_datetime()
    hashed_password = hash_password(user.password)

    cursor.execute('''
        INSERT INTO users (
            id, username, password, email, company, phone, 
            register_time, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id, phone, hashed_password, email, user.company, phone,
        current_time, 1, current_time, current_time
    ))
    conn.commit()
    conn.close()

    create_user_folders(user_id)

    return ResponseHelper.success({
        "user_id": user_id,
        "username": phone,
        "email": email,
        "message": "注册成功"
    }, "用户创建成功")


@router.get("/user/{user_id}")
async def get_user(user_id: str):
    conn = get_main_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, username, email, company, phone, status,
               register_time, last_login_time, avatar_url, role,
               member_type, member_start_at, member_end_at, recognition_used
        FROM users WHERE id = ?
    ''', (user_id,))

    user = cursor.fetchone()
    conn.close()

    if not user:
        return ResponseHelper.error("用户不存在", 404)

    user_dict = dict(user)
    user_dict["phone"] = user_dict.get("phone") or user_dict.get("username")
    user_dict.setdefault("member_type", "normal")
    user_dict.setdefault("member_start_at", None)
    user_dict.setdefault("member_end_at", None)
    user_dict.setdefault("recognition_used", 0)

    # 供前端判断是否允许识别及提示
    can_recognize, quota_message = check_recognition_quota(user_id, add_count=0)
    user_dict["can_recognize"] = can_recognize
    user_dict["quota_message"] = quota_message if not can_recognize else ""
    mt = (user_dict.get("member_type") or "normal").strip() or "normal"
    # None 表示不限次数
    user_dict["recognition_quota"] = RECOGNITION_QUOTA_NORMAL if mt == "normal" else None

    return ResponseHelper.success(user_dict, "获取用户信息成功")


@router.put("/user/{user_id}")
async def update_user(user_id: str, user_update: UserUpdate):
    conn = get_main_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not cursor.fetchone():
        conn.close()
        return ResponseHelper.error("用户不存在", 404)

    update_fields = []
    update_values = []

    if user_update.email is not None:
        email_value = user_update.email.strip()
        cursor.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email_value, user_id))
        if cursor.fetchone():
            conn.close()
            return ResponseHelper.error("邮箱已存在", 400)
        update_fields.append("email = ?")
        update_values.append(email_value)

    if user_update.phone is not None:
        phone = user_update.phone.strip()
        if not PHONE_PATTERN.match(phone):
            conn.close()
            return ResponseHelper.error("手机号格式不正确", 400)
        cursor.execute("SELECT id FROM users WHERE username = ? AND id != ?", (phone, user_id))
        if cursor.fetchone():
            conn.close()
            return ResponseHelper.error("手机号已存在", 400)
        update_fields.append("phone = ?")
        update_fields.append("username = ?")
        update_values.append(phone)
        update_values.append(phone)

    if user_update.company is not None:
        update_fields.append("company = ?")
        update_values.append(user_update.company)

    if user_update.avatar_url is not None:
        update_fields.append("avatar_url = ?")
        update_values.append(user_update.avatar_url)

    if not update_fields:
        conn.close()
        return ResponseHelper.error("没有可更新的字段", 400)

    update_fields.append("updated_at = ?")
    update_values.append(format_datetime())
    update_values.append(user_id)

    query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
    cursor.execute(query, update_values)
    conn.commit()
    conn.close()

    return ResponseHelper.success({"message": "用户信息更新成功"}, "更新成功")


@router.delete("/user/{user_id}")
async def delete_user(user_id: str):
    conn = get_main_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not cursor.fetchone():
        conn.close()
        return ResponseHelper.error("用户不存在", 404)

    import shutil
    user_db_path = config.get_user_db_path(user_id)
    if os.path.exists(user_db_path):
        os.remove(user_db_path)

    user_dir = config.get_user_dir(user_id)
    if os.path.exists(user_dir):
        shutil.rmtree(user_dir)

    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

    return ResponseHelper.success({"deleted": True}, "用户删除成功")