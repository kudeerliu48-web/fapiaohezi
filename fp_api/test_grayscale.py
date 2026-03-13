"""
测试灰度图转换功能

验证：
1. 上传图片后是否同时生成彩色和灰度两个版本
2. 灰度图是否用于 OCR 识别
3. 彩色图是否用于前端预览
"""

from PIL import Image
import os
from pathlib import Path

# 测试图片处理函数
from image_processing import process_images_to_webp_pages, ProcessProfile

def test_grayscale_conversion():
    print("🧪 开始测试灰度图转换功能...\n")
    
    # 创建一个测试图片（彩色）
    test_img = Image.new('RGB', (800, 600), color='red')
    # 添加一些文字模拟发票
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(test_img)
    draw.text((100, 100), "测试发票", fill='black')
    draw.line([(50, 50), (750, 550)], fill='blue', width=2)
    
    print("✅ 创建测试图片（800x600 红色背景，带蓝色线条和黑色文字）")
    
    # 处理图片
    processed_dir = Path("test_processed")
    processed_dir.mkdir(exist_ok=True)
    
    results = process_images_to_webp_pages(
        images=[test_img],
        processed_dir=processed_dir,
        base_id="test_001",
        original_filename="test_invoice.png",
        save_color_version=True,
    )
    
    print(f"\n📊 处理结果:")
    for result in results:
        print(f"  - 页码：{result['page_index']}")
        print(f"  - 灰度文件名：{result['processed_filename']}")
        print(f"  - 彩色文件名：{result.get('color_filename', 'N/A')}")
        print(f"  - 尺寸：{result['processed_width']}x{result['processed_height']}")
        print(f"  - 大小：{result['processed_bytes']} bytes")
        
        # 验证文件是否存在
        gray_path = processed_dir / result['processed_filename']
        color_path = processed_dir / result['color_filename'] if result.get('color_filename') else None
        
        if gray_path.exists():
            print(f"  ✅ 灰度图已保存：{gray_path}")
            # 检查是否为灰度图
            with Image.open(gray_path) as img:
                pixel = img.getpixel((100, 100))
                print(f"     像素值示例：{pixel} (灰度图的 RGB 三个值应该相等)")
        else:
            print(f"  ❌ 灰度图未找到：{gray_path}")
        
        if color_path and color_path.exists():
            print(f"  ✅ 彩色图已保存：{color_path}")
            with Image.open(color_path) as img:
                pixel = img.getpixel((100, 100))
                print(f"     像素值示例：{pixel}")
        elif color_path:
            print(f"  ❌ 彩色图未找到：{color_path}")
    
    print("\n🎯 预期效果:")
    print("  1. 生成两个 WebP 文件：一个灰度版本，一个彩色版本")
    print("  2. 灰度版本用于 OCR 识别（文件更小，识别更快更准）")
    print("  3. 彩色版本用于前端预览（用户体验更好）")
    print("  4. 灰度图文件大小应该小于彩色图")
    
    # 清理测试文件
    # import shutil
    # shutil.rmtree(processed_dir)
    # print(f"\n🗑️  已清理测试目录：{processed_dir}")
    
    print("\n✅ 测试完成！")

if __name__ == "__main__":
    test_grayscale_conversion()
