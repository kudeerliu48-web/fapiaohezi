from datetime import datetime
from typing import Any, Optional


def format_datetime(dt: Optional[datetime] = None) -> str:
    """格式化日期时间"""
    if dt is None:
        dt = datetime.now()
    return dt.isoformat()


class ResponseHelper:
    """响应助手"""

    @staticmethod
    def success(data: Any = None, message: str = "操作成功"):
        """成功响应"""
        return {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": format_datetime()
        }

    @staticmethod
    def error(message: str, code: int = 400, data: Any = None):
        """错误响应"""
        return {
            "success": False,
            "message": message,
            "code": code,
            "data": data,
            "timestamp": format_datetime()
        }

    @staticmethod
    def paginated(data: list, total: int, page: int, limit: int):
        """分页响应"""
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
