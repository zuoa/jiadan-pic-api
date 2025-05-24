#!/usr/bin/env python3
"""
简单的API测试脚本
使用Flask测试客户端直接测试API
"""

from app import app
import json

def test_api():
    """测试API功能"""
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        print("🚀 开始API测试...\n")
        
        # 测试登录
        print("🔐 测试登录接口...")
        response = client.post('/api/auth/login', 
                             json={'username': 'admin', 'password': 'password'},
                             content_type='application/json')
        
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.get_json()}")
        
        if response.status_code == 200:
            data = response.get_json()
            if data.get('success'):
                token = data['data']['token']
                print(f"✅ 登录成功! Token: {token[:20]}...")
                
                # 测试Token验证
                print("\n🔍 测试Token验证接口...")
                headers = {'Authorization': f'Bearer {token}'}
                response = client.get('/api/auth/verify', headers=headers)
                print(f"状态码: {response.status_code}")
                print(f"响应: {response.get_json()}")
                
                # 测试获取照片列表
                print("\n📷 测试获取照片列表接口...")
                response = client.get('/api/photos', headers=headers)
                print(f"状态码: {response.status_code}")
                print(f"响应: {response.get_json()}")
                
                # 测试统计接口
                print("\n📊 测试仪表板统计接口...")
                response = client.get('/api/dashboard/stats', headers=headers)
                print(f"状态码: {response.status_code}")
                print(f"响应: {response.get_json()}")
                
                print("\n✅ 所有测试完成!")
            else:
                print(f"❌ 登录失败: {data}")
        else:
            print(f"❌ 登录请求失败: {response.status_code}")
        
        # 测试公开接口
        print("\n🌐 测试公开照片接口...")
        response = client.get('/api/public/photos')
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.get_json()}")

if __name__ == "__main__":
    test_api() 