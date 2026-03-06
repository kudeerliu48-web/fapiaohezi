import sqlite3
import os
import shutil
import sys

print('🗑️  开始清空数据...')
print()

# 1. 清空主数据库中的用户数据
db_path = 'main.db'
if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 删除所有用户（除了可能的管理员）
        print('📝 清空主数据库...')
        cursor.execute('DELETE FROM users WHERE username != "admin"')
        cursor.execute('DELETE FROM login_logs')
        
        conn.commit()
        conn.close()
        print('✅ 已清空主数据库中的用户数据')
    except Exception as e:
        print(f'❌ 清空主数据库失败：{e}')
else:
    print('⚠️  主数据库文件不存在')

print()

# 2. 删除 files 目录下的所有用户文件夹
files_dir = 'files'
if os.path.exists(files_dir):
    print('📝 清空 files 目录...')
    deleted_count = 0
    failed_items = []
    
    for item in os.listdir(files_dir):
        item_path = os.path.join(files_dir, item)
        try:
            if os.path.isdir(item_path):
                shutil.rmtree(item_path, ignore_errors=True)
                deleted_count += 1
                print(f'✅ 已删除目录：{item}')
            else:
                os.remove(item_path)
                deleted_count += 1
                print(f'✅ 已删除文件：{item}')
        except Exception as e:
            print(f'❌ 删除 {item} 失败：{e}')
            failed_items.append(item)
    
    print(f'\n✅ 成功删除 {deleted_count} 个项目')
    if failed_items:
        print(f'⚠️  以下项目删除失败（可能被占用）: {", ".join(failed_items)}')
        print(f'💡 提示：请重启电脑后再运行此脚本，或手动删除这些文件')
else:
    print('⚠️  files 目录不存在')

print()
print('✅ 数据清空完成！')
print()
print('📋 提示：')
print('   - 管理员账号已保留')
print('   - 所有用户数据已删除')
print('   - 所有用户上传的文件已删除')
print('   - 重启服务后需要重新注册账号')
print()

if failed_items:
    input(f"\n有 {len(failed_items)} 个文件无法删除，按回车键退出...")
    sys.exit(1)
else:
    input("\n所有数据已清空，按回车键退出...")
