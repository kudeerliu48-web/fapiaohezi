import os
from typing import Optional


class Config:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///main.db")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "files")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    API_V1_PREFIX: str = "/api"
    ALLOWED_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".pdf", ".tiff", ".bmp", ".webp"}
    MAX_UPLOAD_FILE_SIZE: int = 300 * 1024

    # 对外暴露自身服务地址（供生成文件 URL 等使用）
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")

    V9_API_BASE_URL: str = os.getenv("V9_API_BASE_URL", "http://182.92.151.50:12001")
    V9_API_KEY: str = os.getenv("V9_API_KEY", "sk-QgFDWUDraWz4YJkbm35eWfcHL30wB7YtggHluM4uzjo")
    V9_POLL_INTERVAL: float = float(os.getenv("V9_POLL_INTERVAL", "1.0"))
    V9_POLL_TIMEOUT: float = float(os.getenv("V9_POLL_TIMEOUT", "600.0"))

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
    def get_database_dir(cls, user_id: str) -> str:
        return os.path.join(cls.UPLOAD_DIR, user_id, "database")

    @classmethod
    def get_user_db_path(cls, user_id: str) -> str:
        return os.path.join(cls.get_database_dir(user_id), f"{user_id}.db")


config = Config()
