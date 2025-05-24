#!/usr/bin/env python3
"""
创建测试图片的脚本
生成简单的测试图片用于API测试
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_test_image(filename="test_image.jpg", width=800, height=600):
    """创建一个简单的测试图片"""
    
    # 创建图片
    image = Image.new('RGB', (width, height), color='skyblue')
    draw = ImageDraw.Draw(image)
    
    # 添加一些几何图形
    # 绘制矩形
    draw.rectangle([100, 100, 300, 250], fill='lightcoral', outline='darkred', width=3)
    
    # 绘制圆形
    draw.ellipse([400, 150, 600, 350], fill='lightgreen', outline='darkgreen', width=3)
    
    # 绘制线条
    draw.line([50, 50, width-50, height-50], fill='purple', width=5)
    draw.line([width-50, 50, 50, height-50], fill='orange', width=5)
    
    # 添加文字
    try:
        # 尝试使用系统字体
        font = ImageFont.truetype("Arial.ttf", 36)
    except:
        # 如果没有找到字体，使用默认字体
        font = ImageFont.load_default()
    
    text = "Test Image"
    try:
        # 新版本Pillow使用textbbox
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except AttributeError:
        # 旧版本Pillow使用textsize
        text_width, text_height = draw.textsize(text, font=font)
    
    text_x = (width - text_width) // 2
    text_y = height - 100
    
    # 绘制文字背景
    draw.rectangle([text_x-10, text_y-10, text_x+text_width+10, text_y+text_height+10], 
                   fill='white', outline='black')
    
    # 绘制文字
    draw.text((text_x, text_y), text, fill='black', font=font)
    
    # 保存图片
    image.save(filename, 'JPEG', quality=95)
    print(f"✅ 测试图片已创建: {filename}")
    print(f"   尺寸: {width}x{height}")
    print(f"   格式: JPEG")
    print(f"   大小: {os.path.getsize(filename)} 字节")
    
    return filename

def create_multiple_test_images():
    """创建多个不同的测试图片"""
    
    images = [
        ("landscape.jpg", 1200, 800, "风景图"),
        ("portrait.jpg", 600, 800, "人像图"),
        ("square.jpg", 600, 600, "方形图"),
        ("small.jpg", 300, 200, "小图")
    ]
    
    print("🎨 创建测试图片集...")
    
    for filename, width, height, desc in images:
        # 创建不同颜色的背景
        colors = ['lightblue', 'lightpink', 'lightyellow', 'lightgray']
        color = colors[len(images) % len(colors)]
        
        image = Image.new('RGB', (width, height), color=color)
        draw = ImageDraw.Draw(image)
        
        # 添加标识
        try:
            font = ImageFont.truetype("Arial.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        # 绘制描述文字
        try:
            # 新版本Pillow使用textbbox
            bbox = draw.textbbox((0, 0), desc, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except AttributeError:
            # 旧版本Pillow使用textsize
            text_width, text_height = draw.textsize(desc, font=font)
        
        text_x = (width - text_width) // 2
        text_y = (height - text_height) // 2
        
        draw.rectangle([text_x-20, text_y-20, text_x+text_width+20, text_y+text_height+20], 
                       fill='white', outline='black', width=2)
        draw.text((text_x, text_y), desc, fill='black', font=font)
        
        # 添加尺寸信息
        size_text = f"{width}x{height}"
        try:
            # 新版本Pillow使用textbbox
            bbox = draw.textbbox((0, 0), size_text, font=font)
            size_width = bbox[2] - bbox[0]
            size_height = bbox[3] - bbox[1]
        except AttributeError:
            # 旧版本Pillow使用textsize
            size_width, size_height = draw.textsize(size_text, font=font)
        
        draw.text((10, 10), size_text, fill='darkblue', font=font)
        
        # 保存图片
        image.save(filename, 'JPEG', quality=90)
        print(f"  ✅ {filename} ({desc}) - {width}x{height}")
    
    print(f"\n🎉 共创建了 {len(images)} 张测试图片")

def main():
    """主函数"""
    print("测试图片生成器")
    print("=" * 30)
    
    # 创建测试图片目录
    test_dir = "test_images"
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
        print(f"📁 创建测试图片目录: {test_dir}")
    
    # 切换到测试目录
    os.chdir(test_dir)
    
    # 创建单个测试图片
    create_test_image()
    print()
    
    # 创建多个测试图片
    create_multiple_test_images()
    
    print(f"\n📍 图片保存位置: {os.path.abspath('.')}")
    print("\n💡 使用方法:")
    print("  可以将这些图片用于测试图片上传API")
    print("  curl -X POST http://localhost:5000/api/photos/upload \\")
    print("    -H \"Authorization: Bearer <token>\" \\")
    print("    -F \"file=@test_image.jpg\" \\")
    print("    -F \"title=测试图片\"")

if __name__ == "__main__":
    main() 