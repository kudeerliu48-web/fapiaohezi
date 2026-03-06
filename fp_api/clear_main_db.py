import sqlite3

# 清空主数据库中的用户数据
db_path = 'main.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 删除所有用户（除了可能的管理员）
cursor.execute('DELETE FROM users WHERE username != "admin"')
cursor.execute('DELETE FROM login_logs')

conn.commit()
conn.close()
print('✅ 已清空主数据库中的用户数据')
