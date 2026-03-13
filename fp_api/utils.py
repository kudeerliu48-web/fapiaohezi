import random
import string
import os
import uuid
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional
import sqlite3

def generate_uuid() -> str:
    """生成18位纯数字UUID"""
    return ''.join(random.choices(string.digits, k=18))

def hash_password(password: str) -> str:
    """密码SHA256加密"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return hash_password(plain_password) == hashed_password

def create_user_folders(user_id: str, base_dir: str = "files") -> bool:
    """创建用户文件夹结构"""
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

def init_user_database(user_id: str, db_path: str) -> bool:
    """初始化用户数据库"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 发票明细表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoice_details (
                id TEXT PRIMARY KEY,
                batch_id TEXT,
                filename TEXT NOT NULL,
                saved_filename TEXT,
                processed_filename TEXT,
                color_filename TEXT,
                original_file_path TEXT,
                processed_file_path TEXT,
                page_index INTEGER,
                invoice_amount REAL,
                buyer TEXT,
                seller TEXT,
                invoice_number TEXT,
                invoice_date TEXT,
                service_name TEXT,
                amount_without_tax REAL,
                tax_amount REAL,
                total_with_tax REAL,
                final_json TEXT,
                total_duration_ms REAL,
                recognition_status INTEGER DEFAULT 0,
                processing_time REAL,
                ocr_text TEXT,
                json_info TEXT,
                file_type TEXT,
                file_size INTEGER,
                upload_time TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                field1 TEXT,
                field2 TEXT,
                field3 TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS batches (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'processing',
                total_invoices INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                total_duration_ms REAL DEFAULT 0,
                remark TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoice_steps (
                id TEXT PRIMARY KEY,
                invoice_id TEXT NOT NULL,
                batch_id TEXT,
                step_name TEXT NOT NULL,
                step_order INTEGER DEFAULT 0,
                status TEXT NOT NULL,
                started_at TEXT,
                ended_at TEXT,
                duration_ms REAL,
                input_payload TEXT,
                output_payload TEXT,
                error_message TEXT,
                debug_meta TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoice_details_batch_id ON invoice_details(batch_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoice_details_upload_time ON invoice_details(upload_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_batches_created_at ON batches(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoice_steps_invoice_id ON invoice_steps(invoice_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoice_steps_batch_id ON invoice_steps(batch_id)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_invoice_steps_invoice_step_unique ON invoice_steps(invoice_id, step_name)")

        # 兼容迁移：为已存在的表补齐新增字段
        cursor.execute("PRAGMA table_info(invoice_details)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        if 'saved_filename' not in existing_columns:
            cursor.execute("ALTER TABLE invoice_details ADD COLUMN saved_filename TEXT")

        if 'processed_filename' not in existing_columns:
            cursor.execute("ALTER TABLE invoice_details ADD COLUMN processed_filename TEXT")

        if 'page_index' not in existing_columns:
            cursor.execute("ALTER TABLE invoice_details ADD COLUMN page_index INTEGER")

        if 'invoice_date' not in existing_columns:
            cursor.execute("ALTER TABLE invoice_details ADD COLUMN invoice_date TEXT")

        if 'batch_id' not in existing_columns:
            cursor.execute("ALTER TABLE invoice_details ADD COLUMN batch_id TEXT")

        if 'original_file_path' not in existing_columns:
            cursor.execute("ALTER TABLE invoice_details ADD COLUMN original_file_path TEXT")

        if 'processed_file_path' not in existing_columns:
            cursor.execute("ALTER TABLE invoice_details ADD COLUMN processed_file_path TEXT")

        if 'color_filename' not in existing_columns:
            cursor.execute("ALTER TABLE invoice_details ADD COLUMN color_filename TEXT")

        if 'service_name' not in existing_columns:
            cursor.execute("ALTER TABLE invoice_details ADD COLUMN service_name TEXT")

        if 'amount_without_tax' not in existing_columns:
            cursor.execute("ALTER TABLE invoice_details ADD COLUMN amount_without_tax REAL")

        if 'tax_amount' not in existing_columns:
            cursor.execute("ALTER TABLE invoice_details ADD COLUMN tax_amount REAL")

        if 'total_with_tax' not in existing_columns:
            cursor.execute("ALTER TABLE invoice_details ADD COLUMN total_with_tax REAL")

        if 'final_json' not in existing_columns:
            cursor.execute("ALTER TABLE invoice_details ADD COLUMN final_json TEXT")

        if 'total_duration_ms' not in existing_columns:
            cursor.execute("ALTER TABLE invoice_details ADD COLUMN total_duration_ms REAL")
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"初始化用户数据库失败: {e}")
        return False

def format_datetime(dt: Optional[datetime] = None) -> str:
    """格式化日期时间"""
    if dt is None:
        dt = datetime.now()
    return dt.isoformat()

def parse_datetime(dt_str: str) -> datetime:
    """解析日期时间字符串"""
    return datetime.fromisoformat(dt_str)

def safe_json_loads(json_str: str) -> Dict[str, Any]:
    """安全的JSON解析"""
    try:
        return json.loads(json_str) if json_str else {}
    except json.JSONDecodeError:
        return {}

def safe_json_dumps(data: Dict[str, Any]) -> str:
    """安全的JSON序列化"""
    try:
        return json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError):
        return "{}"

def get_file_extension(filename: str) -> str:
    """获取文件扩展名"""
    return os.path.splitext(filename)[1].lower() if '.' in filename else ''

def is_allowed_file(filename: str, allowed_extensions: set) -> bool:
    """检查文件类型是否允许"""
    extension = get_file_extension(filename)
    return extension in allowed_extensions

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

class DatabaseManager:
    """数据库管理器"""
    
    @staticmethod
    def get_connection(db_path: str):
        """获取数据库连接"""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # 返回字典格式
        return conn
    
    @staticmethod
    def execute_query(conn, query: str, params: tuple = None):
        """执行查询"""
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor
    
    @staticmethod
    def execute_many(conn, query: str, params_list: list):
        """批量执行"""
        cursor = conn.cursor()
        cursor.executemany(query, params_list)
        return cursor

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
