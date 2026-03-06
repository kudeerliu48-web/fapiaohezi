import sqlite3
import os

print('🔧 开始数据库迁移 - 添加 color_filename 字段...\n')

# 获取所有用户数据库目录
files_dir = 'files'
if not os.path.exists(files_dir):
    print('❌ files 目录不存在')
    exit(1)

updated_count = 0
failed_count = 0

for user_id in os.listdir(files_dir):
    user_db_path = os.path.join(files_dir, user_id, 'database', f'{user_id}.db')
    
    if not os.path.exists(user_db_path):
        print(f'⚠️  跳过不存在的数据库：{user_id}')
        continue
    
    try:
        conn = sqlite3.connect(user_db_path)
        cursor = conn.cursor()
        
        # 检查字段是否存在
        cursor.execute('PRAGMA table_info(invoice_details)')
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'color_filename' in columns:
            print(f'✅ {user_id}: color_filename 字段已存在')
            conn.close()
            continue
        
        # 添加字段
        cursor.execute('ALTER TABLE invoice_details ADD COLUMN color_filename TEXT')
        conn.commit()
        conn.close()
        
        print(f'✅ {user_id}: 成功添加 color_filename 字段')
        updated_count += 1
        
    except Exception as e:
        print(f'❌ {user_id}: 迁移失败 - {e}')
        failed_count += 1

print(f'\n{"="*60}')
print(f'✅ 数据库迁移完成！')
print(f'   成功：{updated_count} 个数据库')
print(f'   失败：{failed_count} 个数据库')
print(f'{"="*60}\n')

if failed_count > 0:
    print('💡 提示：部分数据库迁移失败，请检查错误信息')
else:
    print('🎉 所有数据库已成功更新！')
