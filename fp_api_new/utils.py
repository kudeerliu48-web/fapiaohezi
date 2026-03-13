import random
import string
import os
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi.responses import JSONResponse


def generate_uuid() -> str:
    return ''.join(random.choices(string.digits, k=18))


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password


def create_user_folders(user_id: str, base_dir: str = "files") -> bool:
    try:
        folders = [
            os.path.join(base_dir, user_id),
            os.path.join(base_dir, user_id, "database"),
            os.path.join(base_dir, user_id, "uploads"),
            os.path.join(base_dir, user_id, "processed")
        ]
        for folder in folders:
            os.makedirs(folder, exist_ok=True)
        return True
    except Exception as e:
        print(f"创建用户文件夹失败: {e}")
        return False


def format_datetime(dt: Optional[datetime] = None) -> str:
    if dt is None:
        dt = datetime.now()
    return dt.isoformat()


def safe_json_loads(json_str: str) -> Dict[str, Any]:
    try:
        return json.loads(json_str) if json_str else {}
    except json.JSONDecodeError:
        return {}


def safe_json_dumps(data: Dict[str, Any]) -> str:
    try:
        return json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError):
        return "{}"


def get_file_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower() if '.' in filename else ''


def is_allowed_file(filename: str, allowed_extensions: set) -> bool:
    extension = get_file_extension(filename)
    return extension in allowed_extensions


def format_file_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f} {size_names[i]}"


class ResponseHelper:
    @staticmethod
    def success(data: Any = None, message: str = "操作成功"):
        return {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": format_datetime()
        }

    @staticmethod
    def error(message: str, code: int = 400, data: Any = None):
        return {
            "success": False,
            "message": message,
            "code": code,
            "data": data,
            "timestamp": format_datetime()
        }

    @staticmethod
    def paginated(data: list, total: int, page: int, limit: int):
        return {
            "success": True,
            "data": data,
            "pagination": {
                "total": total,
                "page": page,
                "limit": limit,
                "pages": (total + limit - 1) // limit
            },
            "timestamp": format_datetime()
        }
