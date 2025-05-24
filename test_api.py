#!/usr/bin/env python3
"""
图片管理系统API测试脚本
用于测试主要的API接口功能
"""

import requests
import json
import os

# API基础URL
BASE_URL = "http://localhost:9000"

class APITester:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.token = None
        self.session = requests.Session()
    
    def test_login(self, username="admin", password="password"):
        """测试登录接口"""
        print("🔐 测试登录接口...")
        
        url = f"{self.base_url}/api/auth/login"
        data = {
            "username": username,
            "password": password
        }
        
        response = self.session.post(url, json=data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                self.token = result['data']['token']
                print(f"✅ 登录成功! Token: {self.token[:20]}...")
                return True
            else:
                print(f"❌ 登录失败: {result.get('error', {}).get('message', '未知错误')}")
        else:
            print(f"❌ 登录请求失败: HTTP {response.status_code}")
        
        return False
    
    def test_verify_token(self):
        """测试Token验证接口"""
        print("🔍 测试Token验证接口...")
        
        if not self.token:
            print("❌ 没有有效的Token")
            return False
        
        url = f"{self.base_url}/api/auth/verify"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = self.session.get(url, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                user = result['data']['user']
                print(f"✅ Token验证成功! 用户: {user['username']} ({user['email']})")
                return True
        
        print(f"❌ Token验证失败: HTTP {response.status_code}")
        return False
    
    def test_get_photos(self):
        """测试获取照片列表接口"""
        print("📷 测试获取照片列表接口...")
        
        if not self.token:
            print("❌ 没有有效的Token")
            return False
        
        url = f"{self.base_url}/api/photos"
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {
            "page": 1,
            "size": 10,
            "sort": "date",
            "order": "desc"
        }
        
        response = self.session.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                photos = result['data']['photos']
                pagination = result['data']['pagination']
                print(f"✅ 获取照片列表成功! 共 {pagination['total']} 张照片")
                return True
        
        print(f"❌ 获取照片列表失败: HTTP {response.status_code}")
        return False
    
    def test_dashboard_stats(self):
        """测试仪表板统计接口"""
        print("📊 测试仪表板统计接口...")
        
        if not self.token:
            print("❌ 没有有效的Token")
            return False
        
        url = f"{self.base_url}/api/dashboard/stats"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = self.session.get(url, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                stats = result['data']
                print(f"✅ 获取统计信息成功!")
                print(f"   总照片数: {stats['totalPhotos']}")
                print(f"   总大小: {stats['totalSize']}")
                print(f"   本月上传: {stats['thisMonth']}")
                print(f"   公开照片: {stats['publicPhotos']}")
                print(f"   私有照片: {stats['privatePhotos']}")
                return True
        
        print(f"❌ 获取统计信息失败: HTTP {response.status_code}")
        return False
    
    def test_public_photos(self):
        """测试公开照片接口"""
        print("🌐 测试公开照片接口...")
        
        url = f"{self.base_url}/api/public/photos"
        params = {"page": 1, "size": 12}
        
        response = self.session.get(url, params=params)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                photos = result['data']['photos']
                pagination = result['data']['pagination']
                print(f"✅ 获取公开照片列表成功! 共 {pagination['total']} 张公开照片")
                return True
        
        print(f"❌ 获取公开照片列表失败: HTTP {response.status_code}")
        return False
    
    def test_logout(self):
        """测试登出接口"""
        print("👋 测试登出接口...")
        
        if not self.token:
            print("❌ 没有有效的Token")
            return False
        
        url = f"{self.base_url}/api/auth/logout"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = self.session.post(url, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ 登出成功!")
                self.token = None
                return True
        
        print(f"❌ 登出失败: HTTP {response.status_code}")
        return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始API测试...\n")
        
        tests = [
            self.test_login,
            self.test_verify_token,
            self.test_get_photos,
            self.test_dashboard_stats,
            self.test_public_photos,
            self.test_logout
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ 测试异常: {e}")
                failed += 1
            print()
        
        print(f"📋 测试完成!")
        print(f"✅ 通过: {passed}")
        print(f"❌ 失败: {failed}")
        print(f"📊 成功率: {passed/(passed+failed)*100:.1f}%")

def main():
    """主函数"""
    print("图片管理系统API测试工具")
    print("=" * 40)
    
    # 检查服务器是否运行
    try:
        response = requests.get(BASE_URL, timeout=5)
        print(f"🌐 服务器状态: 正常 (HTTP {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接到服务器: {e}")
        print("请确保Flask应用正在运行 (python app.py)")
        return
    
    print()
    
    # 运行测试
    tester = APITester()
    tester.run_all_tests()

if __name__ == "__main__":
    main() 