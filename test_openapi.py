#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试 OpenAPI 功能的脚本
"""

def test_flask_restx_import():
    """测试 Flask-RESTX 是否可以正常导入"""
    try:
        from flask_restx import Api, Resource, fields, Namespace
        print("✅ Flask-RESTX 导入成功")
        return True
    except ImportError as e:
        print(f"❌ Flask-RESTX 导入失败: {e}")
        print("请安装 flask-restx: pip install flask-restx==1.3.0")
        return False

def test_app_creation():
    """测试应用创建"""
    try:
        from app_openapi import app, api
        print("✅ OpenAPI 应用创建成功")
        print(f"   - API 标题: {api.title}")
        print(f"   - API 版本: {api.version}")
        print(f"   - API 文档路径: {api.doc}")
        return True
    except Exception as e:
        print(f"❌ OpenAPI 应用创建失败: {e}")
        return False

def test_api_endpoints():
    """测试 API 端点"""
    try:
        from app_openapi import app
        with app.test_client() as client:
            # 测试 API 文档是否可访问
            response = client.get('/api/docs/')
            if response.status_code == 200:
                print("✅ API 文档页面可访问")
            else:
                print(f"⚠️  API 文档页面状态码: {response.status_code}")
            
            # 测试 swagger.json 是否生成
            response = client.get('/api/swagger.json')
            if response.status_code == 200:
                print("✅ OpenAPI 规范 JSON 可访问")
                data = response.get_json()
                print(f"   - OpenAPI 版本: {data.get('swagger', 'N/A')}")
                print(f"   - 端点数量: {len(data.get('paths', {}))}")
            else:
                print(f"❌ OpenAPI 规范 JSON 访问失败: {response.status_code}")
            
            return True
    except Exception as e:
        print(f"❌ API 端点测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🔍 开始测试 OpenAPI 功能...\n")
    
    success_count = 0
    total_tests = 3
    
    # 测试 1: 依赖导入
    if test_flask_restx_import():
        success_count += 1
    
    print()
    
    # 测试 2: 应用创建
    if test_app_creation():
        success_count += 1
    
    print()
    
    # 测试 3: API 端点
    if test_api_endpoints():
        success_count += 1
    
    print("\n" + "="*50)
    print(f"测试结果: {success_count}/{total_tests} 通过")
    
    if success_count == total_tests:
        print("🎉 所有测试通过！可以启动 OpenAPI 应用")
        print("\n启动命令:")
        print("python run_openapi.py")
        print("\nAPI 文档地址:")
        print("http://localhost:5000/api/docs/")
    else:
        print("⚠️  部分测试失败，请检查依赖安装")
        print("\n安装依赖命令:")
        print("pip install flask-restx==1.3.0")

if __name__ == '__main__':
    main() 