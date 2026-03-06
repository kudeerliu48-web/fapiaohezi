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
    
    # API配置
    API_V1_PREFIX: str = "/api"
    
    # 文件类型限制
    ALLOWED_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".pdf", ".tiff", ".bmp", ".webp"}
    
    @classmethod
    def get_upload_dir(cls, user_id: str) -> str:
        """获取用户上传目录"""
        return os.path.join(cls.UPLOAD_DIR, user_id, "uploads")
    
    @classmethod
    def get_processed_dir(cls, user_id: str) -> str:
        """获取用户处理后文件目录"""
        return os.path.join(cls.UPLOAD_DIR, user_id, "processed")
    
    @classmethod
    def get_database_dir(cls, user_id: str) -> str:
        """获取用户数据库目录"""
        return os.path.join(cls.UPLOAD_DIR, user_id, "database")
    
    @classmethod
    def get_user_db_path(cls, user_id: str) -> str:
        """获取用户数据库路径"""
        return os.path.join(cls.get_database_dir(user_id), f"{user_id}.db")

config = Config()
