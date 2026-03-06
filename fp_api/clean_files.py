import os
import shutil
import time

files_dir = 'files'

if os.path.exists(files_dir):
    print('🗑️  开始清空 files 目录...')
    for item in os.listdir(files_dir):
        item_path = os.path.join(files_dir, item)
        try:
            if os.path.isdir(item_path):
                # 尝试多次删除，处理文件占用问题
                for i in range(3):
                    try:
                        shutil.rmtree(item_path)
                        print(f'✅ 已删除：{item}')
                        break
                    except (PermissionError, OSError) as e:
                        print(f'⚠️  第 {i+1} 次尝试删除 {item} 失败，等待 2 秒...')
                        time.sleep(2)
                else:
                    print(f'❌ 删除 {item} 失败：文件被占用')
            else:
                os.remove(item_path)
                print(f'✅ 已删除：{item}')
        except Exception as e:
            print(f'❌ 删除 {item} 失败：{e}')
    
    # 检查是否还有残留
    remaining = os.listdir(files_dir)
    if remaining:
        print(f'\n⚠️  仍有残留目录：{remaining}')
    else:
        print('\n✅ files 目录已完全清空！')
else:
    print('⚠️  files 目录不存在')
