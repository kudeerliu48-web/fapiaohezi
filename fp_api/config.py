import os
from typing import Optional


class Config:
    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///main.db")

    # 文件上传配置
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "files")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB

    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")

    # API 配置
    API_V1_PREFIX: str = "/api"

    # 文件类型限制
    ALLOWED_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".pdf", ".tiff", ".bmp", ".webp"}

    # V9 外部识别 API
    V9_API_BASE_URL: str = os.getenv("V9_API_BASE_URL", "http://182.92.151.50:12001")
    V9_API_KEY: str = os.getenv("V9_API_KEY", "")
    V9_POLL_INTERVAL: float = float(os.getenv("V9_POLL_INTERVAL", "2.0"))
    V9_POLL_TIMEOUT: float = float(os.getenv("V9_POLL_TIMEOUT", "600.0"))

    # 短信配置（阿里云接口预留）
    ALIYUN_SMS_ACCESS_KEY_ID: str = os.getenv("ALIYUN_SMS_ACCESS_KEY_ID", "")
    ALIYUN_SMS_ACCESS_KEY_SECRET: str = os.getenv("ALIYUN_SMS_ACCESS_KEY_SECRET", "")
    ALIYUN_SMS_SIGN_NAME: str = os.getenv("ALIYUN_SMS_SIGN_NAME", "")
    ALIYUN_SMS_TEMPLATE_CODE: str = os.getenv("ALIYUN_SMS_TEMPLATE_CODE", "")
    SMS_MOCK_MODE: bool = os.getenv("SMS_MOCK_MODE", "true").lower() in {"1", "true", "yes", "on"}
    SMS_CODE_EXPIRE_SECONDS: int = int(os.getenv("SMS_CODE_EXPIRE_SECONDS", "300"))

    @classmethod
    def get_upload_dir(cls, user_id: str) -> str:
        return os.path.join(cls.UPLOAD_DIR, user_id, "uploads")

    @classmethod
    def get_user_dir(cls, user_id: str) -> str:
        return os.path.join(cls.UPLOAD_DIR, user_id)

    @classmethod
    def get_processed_dir(cls, user_id: str) -> str:
        return os.path.join(cls.UPLOAD_DIR, user_id, "processed")

    @classmethod
    def get_debug_dir(cls, user_id: str, invoice_id: Optional[str] = None) -> str:
        base = os.path.join(cls.UPLOAD_DIR, user_id, "debug")
        if invoice_id:
            return os.path.join(base, invoice_id)
        return base

    @classmethod
    def get_database_dir(cls, user_id: str) -> str:
        return os.path.join(cls.UPLOAD_DIR, user_id, "database")

    @classmethod
    def get_user_db_path(cls, user_id: str) -> str:
        return os.path.join(cls.get_database_dir(user_id), f"{user_id}.db")


config = Config()
