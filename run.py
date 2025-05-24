#!/usr/bin/env python3
"""
图片管理系统启动脚本
提供便捷的启动和测试选项
"""

import sys
import os
import subprocess
import argparse

def install_dependencies():
    """安装依赖"""
    print("📦 安装项目依赖...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ 依赖安装完成!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        return False

def setup_environment():
    """设置环境"""
    print("⚙️ 设置环境...")
    
    # 检查.env文件
    if not os.path.exists('.env'):
        if os.path.exists('env.example'):
            print("📄 复制环境变量示例文件...")
            with open('env.example', 'r') as src, open('.env', 'w') as dst:
                dst.write(src.read())
            print("✅ .env文件创建完成!")
        else:
            print("⚠️ 环境变量示例文件不存在，请手动创建.env文件")
    else:
        print("✅ .env文件已存在")
    
    # 创建上传目录
    upload_dir = "uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir, exist_ok=True)
        print(f"✅ 创建上传目录: {upload_dir}")
    
    return True

def run_server():
    """启动服务器"""
    print("🚀 启动Flask应用...")
    try:
        from app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except ImportError as e:
        print(f"❌ 导入应用失败: {e}")
        print("请确保已安装所有依赖: python run.py --install")
        return False
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return False

def run_tests():
    """运行API测试"""
    print("🧪 运行API测试...")
    try:
        subprocess.check_call([sys.executable, "test_api.py"])
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 测试执行失败: {e}")
        return False
    except FileNotFoundError:
        print("❌ 测试文件不存在")
        return False

def init_project():
    """初始化项目"""
    print("🎯 初始化图片管理系统项目...")
    print("=" * 50)
    
    steps = [
        ("安装依赖", install_dependencies),
        ("设置环境", setup_environment),
    ]
    
    for step_name, step_func in steps:
        print(f"\n📋 {step_name}...")
        if not step_func():
            print(f"❌ {step_name}失败，请检查错误信息")
            return False
        print(f"✅ {step_name}完成")
    
    print("\n🎉 项目初始化完成!")
    print("\n接下来您可以:")
    print("  🚀 启动服务: python run.py --server")
    print("  🧪 运行测试: python run.py --test")
    print("  📖 查看文档: cat README.md")
    
    return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="图片管理系统启动脚本")
    parser.add_argument("--init", action="store_true", help="初始化项目")
    parser.add_argument("--install", action="store_true", help="安装依赖")
    parser.add_argument("--server", action="store_true", help="启动服务器")
    parser.add_argument("--test", action="store_true", help="运行API测试")
    parser.add_argument("--setup", action="store_true", help="设置环境")
    
    args = parser.parse_args()
    
    # 如果没有参数，显示帮助
    if not any(vars(args).values()):
        parser.print_help()
        print("\n💡 快速开始:")
        print("  python run.py --init    # 初始化项目")
        print("  python run.py --server  # 启动服务器")
        print("  python run.py --test    # 运行测试")
        return
    
    # 执行对应的操作
    if args.init:
        init_project()
    elif args.install:
        install_dependencies()
    elif args.setup:
        setup_environment()
    elif args.server:
        run_server()
    elif args.test:
        run_tests()

if __name__ == "__main__":
    main() 