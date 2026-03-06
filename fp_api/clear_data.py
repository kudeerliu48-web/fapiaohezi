import sqlite3
import os
import shutil

print('🗑️  开始清空数据...')

# 1. 清空主数据库中的用户数据
db_path = 'database.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 删除所有用户（除了可能的管理员）
    cursor.execute('DELETE FROM users WHERE username != "admin"')
    cursor.execute('DELETE FROM login_logs')
    
    conn.commit()
    conn.close()
    print('✅ 已清空主数据库中的用户数据')
else:
    print('⚠️  主数据库文件不存在')

# 2. 删除 files 目录下的所有用户文件夹
files_dir = 'files'
if os.path.exists(files_dir):
    for user_id in os.listdir(files_dir):
        user_path = os.path.join(files_dir, user_id)
        if os.path.isdir(user_path):
            try:
                shutil.rmtree(user_path)
                print(f'✅ 已删除用户目录：{user_id}')
            except Exception as e:
                print(f'❌ 删除用户目录 {user_id} 失败：{e}')
    print('✅ 已清空 files 目录')
else:
    print('⚠️  files 目录不存在')

# 3. 删除 user_dbs 目录（如果存在）
user_dbs_dir = 'user_dbs'
if os.path.exists(user_dbs_dir):
    for db_file in os.listdir(user_dbs_dir):
        db_path = os.path.join(user_dbs_dir, db_file)
        try:
            os.remove(db_path)
            print(f'✅ 已删除用户数据库：{db_file}')
        except Exception as e:
            print(f'❌ 删除用户数据库 {db_file} 失败：{e}')
    print('✅ 已清空 user_dbs 目录')
else:
    print('⚠️  user_dbs 目录不存在')

print('\n✅ 数据清空完成！')
print('\n📋 提示：')
print('   - 管理员账号已保留')
print('   - 所有用户数据已删除')
print('   - 所有用户上传的文件已删除')
print('   - 重启服务后需要重新注册账号')
