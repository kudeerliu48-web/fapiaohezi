import sqlite3
import os

db_path = 'files/919207264813097787/database/919207264813097787.db'

if not os.path.exists(db_path):
    print(f'❌ 数据库文件不存在：{db_path}')
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查当前列
cursor.execute('PRAGMA table_info(invoice_details)')
columns = [row[1] for row in cursor.fetchall()]
print('当前列:', columns)

# 需要添加的列
columns_to_add = {
    'batch_id': 'TEXT',
    'saved_filename': 'TEXT',
    'processed_filename': 'TEXT',
    'page_index': 'INTEGER',
    'invoice_date': 'TEXT',
    'original_file_path': 'TEXT',
    'processed_file_path': 'TEXT',
    'service_name': 'TEXT',
    'amount_without_tax': 'REAL',
    'tax_amount': 'REAL',
    'total_with_tax': 'REAL',
    'final_json': 'TEXT',
    'total_duration_ms': 'REAL'
}

# 添加缺失的列
for col_name, col_type in columns_to_add.items():
    if col_name not in columns:
        try:
            cursor.execute(f'ALTER TABLE invoice_details ADD COLUMN {col_name} {col_type}')
            print(f'✅ 已添加列：{col_name}')
        except Exception as e:
            print(f'❌ 添加列 {col_name} 失败：{e}')
    else:
        print(f'⚠️  列 {col_name} 已存在')

conn.commit()
conn.close()

print('\n✅ 数据库迁移完成')
