import sqlite3
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from utils import generate_uuid, format_datetime, safe_json_dumps

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "main.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
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
                field3 TEXT
            )
        ''')
        
        # 登录日志表
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
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def create_user(self, user_data: Dict[str, Any]) -> str:
        """创建用户"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        user_id = generate_uuid()
        current_time = format_datetime()
        
        cursor.execute('''
            INSERT INTO users (
                id, username, password, email, company, phone, 
                register_time, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            user_data['username'],
            user_data['password'],
            user_data['email'],
            user_data.get('company'),
            user_data.get('phone'),
            current_time,
            user_data.get('status', 1),
            current_time,
            current_time
        ))
        
        conn.commit()
        conn.close()
        return user_id
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取用户"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, password, email, company, phone, status, 
                   register_time, last_login_time, avatar_url, role
            FROM users WHERE username = ?
        ''', (username,))
        
        user = cursor.fetchone()
        conn.close()
        
        return dict(user) if user else None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取用户"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, email, company, phone, status, 
                   register_time, last_login_time, avatar_url, role
            FROM users WHERE id = ?
        ''', (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        return dict(user) if user else None
    
    def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """更新用户信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 构建更新语句
        update_fields = []
        update_values = []
        
        for field, value in update_data.items():
            if field in ['email', 'company', 'phone', 'avatar_url']:
                update_fields.append(f"{field} = ?")
                update_values.append(value)
        
        if update_fields:
            update_fields.append("updated_at = ?")
            update_values.append(format_datetime())
            update_values.append(user_id)
            
            query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, update_values)
            conn.commit()
            result = True
        else:
            result = False
        
        conn.close()
        return result
    
    def update_login_time(self, user_id: str) -> bool:
        """更新登录时间"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        current_time = format_datetime()
        cursor.execute('''
            UPDATE users SET login_time = ?, last_login_time = ? WHERE id = ?
        ''', (current_time, current_time, user_id))
        
        conn.commit()
        conn.close()
        return True
    
    def create_login_log(self, user_id: str, ip_address: str = None, 
                       user_agent: str = None, status: int = 1) -> str:
        """创建登录日志"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        log_id = generate_uuid()
        current_time = format_datetime()
        
        cursor.execute('''
            INSERT INTO login_logs (id, user_id, login_time, ip_address, user_agent, login_status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (log_id, user_id, current_time, ip_address, user_agent, status))
        
        conn.commit()
        conn.close()
        return log_id
    
    def user_exists(self, username: str = None, email: str = None) -> bool:
        """检查用户是否存在"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if username:
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        elif email:
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        else:
            conn.close()
            return False
        
        user = cursor.fetchone()
        conn.close()
        return user is not None

class UserDatabaseManager:
    """用户数据库管理器"""
    
    @staticmethod
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

            # 批次表
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

            # 处理步骤表
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
    
    @staticmethod
    def get_connection(db_path: str):
        """获取用户数据库连接"""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    @staticmethod
    def create_invoice_record(user_id: str, db_path: str, invoice_data: Dict[str, Any]) -> str:
        """创建发票记录"""
        conn = UserDatabaseManager.get_connection(db_path)
        cursor = conn.cursor()
        
        invoice_id = generate_uuid()
        current_time = format_datetime()
        
        cursor.execute('''
            INSERT INTO invoice_details (
                id, batch_id, filename, saved_filename, processed_filename, original_file_path, processed_file_path,
                page_index, file_type, file_size, upload_time, recognition_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            invoice_id,
            invoice_data.get('batch_id'),
            invoice_data['filename'],
            invoice_data.get('saved_filename'),
            invoice_data.get('processed_filename'),
            invoice_data.get('original_file_path'),
            invoice_data.get('processed_file_path'),
            invoice_data.get('page_index'),
            invoice_data['file_type'],
            invoice_data['file_size'],
            current_time,
            invoice_data.get('recognition_status', 0),
            current_time,
            current_time
        ))
        
        conn.commit()
        conn.close()
        return invoice_id
    
    @staticmethod
    def update_invoice_recognition(user_id: str, db_path: str, invoice_id: str, 
                               ocr_result: Dict[str, Any]) -> bool:
        """更新发票识别结果"""
        conn = UserDatabaseManager.get_connection(db_path)
        cursor = conn.cursor()
        
        current_time = format_datetime()
        invoice_date = None
        json_info = ocr_result.get('json_info', {})
        if isinstance(json_info, dict):
            invoice_date = (
                json_info.get('invoice_date')
                or (json_info.get('extracted_data', {}) or {}).get('invoice_date')
            )

        # 结构化金额字段补齐
        amount_without_tax = ocr_result.get('amount_without_tax')
        tax_amount = ocr_result.get('tax_amount')
        total_with_tax = ocr_result.get('total_with_tax')

        if total_with_tax is None:
            total_with_tax = ocr_result.get('invoice_amount')

        final_json = ocr_result.get('final_json') if isinstance(ocr_result.get('final_json'), dict) else json_info

        cursor.execute('''
            UPDATE invoice_details 
            SET invoice_amount = ?, buyer = ?, seller = ?, invoice_number = ?,
                invoice_date = ?, recognition_status = ?, processing_time = ?, ocr_text = ?, 
                json_info = ?, service_name = ?, amount_without_tax = ?, tax_amount = ?, total_with_tax = ?,
                final_json = ?, total_duration_ms = ?, updated_at = ?
            WHERE id = ?
        ''', (
            ocr_result.get('invoice_amount'),
            ocr_result.get('buyer'),
            ocr_result.get('seller'),
            ocr_result.get('invoice_number'),
            invoice_date,
            ocr_result.get('recognition_status', 1),
            ocr_result.get('processing_time'),
            ocr_result.get('ocr_text'),
            safe_json_dumps(json_info if isinstance(json_info, dict) else {}),
            ocr_result.get('service_name'),
            amount_without_tax,
            tax_amount,
            total_with_tax,
            safe_json_dumps(final_json if isinstance(final_json, dict) else {}),
            ocr_result.get('total_duration_ms'),
            current_time,
            invoice_id
        ))
        
        conn.commit()
        conn.close()
        return True
    
    @staticmethod
    def get_invoices(user_id: str, db_path: str, page: int = 1, limit: int = 10, keyword: str = None, recognized_only: bool = False) -> Dict[str, Any]:
        """获取发票列表"""
        conn = UserDatabaseManager.get_connection(db_path)
        cursor = conn.cursor()
        
        offset = (page - 1) * limit

        where_clauses = []
        params: List[Any] = []

        if recognized_only:
            where_clauses.append("recognition_status != 0")

        if keyword:
            like = f"%{keyword}%"
            params.extend([like, like, like, like])
            where_clauses.append("(invoice_number LIKE ? OR buyer LIKE ? OR seller LIKE ? OR filename LIKE ?)")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        cursor.execute(
            f'''SELECT id, batch_id, filename, saved_filename, processed_filename, original_file_path, processed_file_path,
                   page_index, invoice_amount, buyer, seller, invoice_number, invoice_date, service_name,
                   amount_without_tax, tax_amount, total_with_tax, final_json, total_duration_ms,
                   recognition_status, processing_time, upload_time, file_type, file_size
            FROM invoice_details 
            {where_sql}
            ORDER BY upload_time DESC 
            LIMIT ? OFFSET ?''',
            (*params, limit, offset),
        )
        
        invoices = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            f"SELECT COUNT(*) as total FROM invoice_details {where_sql}",
            params,
        )
        total = cursor.fetchone()['total']
        
        conn.close()
        
        return {
            'invoices': invoices,
            'total': total,
            'page': page,
            'limit': limit,
            'pages': (total + limit - 1) // limit
        }
    
    @staticmethod
    def get_invoice_by_id(user_id: str, db_path: str, invoice_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取发票详情"""
        conn = UserDatabaseManager.get_connection(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM invoice_details WHERE id = ?
        ''', (invoice_id,))
        
        invoice = cursor.fetchone()
        conn.close()
        
        return dict(invoice) if invoice else None

    @staticmethod
    def delete_invoice(db_path: str, invoice_id: str) -> bool:
        """删除发票记录"""
        conn = UserDatabaseManager.get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM invoice_details WHERE id = ?", (invoice_id,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    @staticmethod
    def delete_invoices(db_path: str, invoice_ids: List[str]) -> int:
        """批量删除发票记录，返回删除条数"""
        if not invoice_ids:
            return 0
        conn = UserDatabaseManager.get_connection(db_path)
        cursor = conn.cursor()
        placeholders = ",".join(["?"] * len(invoice_ids))
        cursor.execute(f"DELETE FROM invoice_details WHERE id IN ({placeholders})", invoice_ids)
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected
