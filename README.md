# 图片管理系统后端API

一个基于Flask的图片管理系统后端服务，支持用户认证、图片上传、管理和展示等功能。

## 功能特性

- **用户认证**: JWT Token认证系统
- **图片管理**: 上传、查看、编辑、删除图片
- **自动缩略图**: 自动生成图片缩略图
- **权限控制**: 用户只能管理自己的图片
- **公开分享**: 支持图片公开分享
- **统计面板**: 提供存储使用情况统计
- **RESTful API**: 标准的REST API设计

## 技术栈

- **框架**: Flask 2.3.3
- **数据库**: SQLite
- **认证**: JWT Token
- **图片处理**: Pillow
- **跨域**: Flask-CORS

## 快速开始

### 方法一：使用便捷启动脚本（推荐）

```bash
# 初始化项目（自动安装依赖和设置环境）
python run.py --init

# 启动服务器
python run.py --server

# 运行API测试
python run.py --test
```

### 方法二：手动操作

#### 1. 安装依赖

```bash
pip install -r requirements.txt
```

#### 2. 配置环境变量

复制环境变量示例文件并修改配置：

```bash
cp env.example .env
```

编辑 `.env` 文件，修改相关配置：

```env
FLASK_ENV=development
SECRET_KEY=your-secret-key-change-in-production-environment
DATABASE_URL=sqlite:///photos.db
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=10485760
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
```

#### 3. 运行应用

```bash
python app.py
```

应用将在 `http://localhost:5000` 启动。

### 4. 默认管理员账户

系统会自动创建默认管理员账户：
- 用户名: `admin`
- 密码: `password`

**生产环境请立即修改默认密码！**

## API接口文档

### 认证接口

#### 登录
```
POST /api/auth/login
Content-Type: application/json

{
    "username": "admin",
    "password": "password"
}
```

#### 登出
```
POST /api/auth/logout
Authorization: Bearer <token>
```

#### 验证Token
```
GET /api/auth/verify
Authorization: Bearer <token>
```

### 照片管理接口

#### 获取照片列表
```
GET /api/photos?page=1&size=10&sort=date&order=desc&public_only=false
Authorization: Bearer <token>
```

#### 获取单张照片
```
GET /api/photos/{photo_id}
Authorization: Bearer <token>
```

#### 上传照片
```
POST /api/photos/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <image_file>
title: "Photo Title" (可选)
description: "Photo Description" (可选)
location: "Location" (可选)
date: "2024-01-15" (可选)
isPublic: true/false (可选，默认false)
```

#### 更新照片信息
```
PUT /api/photos/{photo_id}
Authorization: Bearer <token>
Content-Type: application/json

{
    "title": "Updated Title",
    "description": "Updated Description",
    "location": "Updated Location",
    "date": "2024-01-16",
    "isPublic": true
}
```

#### 删除照片
```
DELETE /api/photos/{photo_id}
Authorization: Bearer <token>
```

### 统计接口

#### 获取仪表板统计
```
GET /api/dashboard/stats
Authorization: Bearer <token>
```

### 公开接口（无需认证）

#### 获取公开照片列表
```
GET /api/public/photos?page=1&size=12
```

#### 获取公开照片详情
```
GET /api/public/photos/{photo_id}
```

## 文件上传限制

- **支持格式**: jpg, jpeg, png, gif, webp
- **文件大小**: 最大 10MB
- **缩略图**: 自动生成 300x200 缩略图
- **存储路径**: `/uploads/photos/{photo_id}/`

## 错误处理

API使用标准的HTTP状态码和统一的错误响应格式：

```json
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "错误描述",
        "details": "详细错误信息"
    }
}
```

常见错误码：
- `400` - 请求参数错误
- `401` - 未认证
- `403` - 无权限
- `404` - 资源不存在
- `413` - 文件过大
- `415` - 不支持的文件类型
- `422` - 验证失败
- `500` - 服务器内部错误

## 目录结构

```
jiadan-pic-api/
├── app.py              # 主应用文件
├── requirements.txt    # Python依赖
├── env.example        # 环境变量示例
├── README.md          # 项目文档
├── uploads/           # 文件上传目录
│   └── photos/        # 照片存储目录
└── photos.db          # SQLite数据库文件
```

## 安全考虑

1. **认证**: 使用JWT Token进行用户认证
2. **文件验证**: 严格验证文件类型和大小
3. **路径安全**: 防止路径遍历攻击
4. **权限控制**: 用户只能管理自己的照片
5. **CORS**: 配置合适的跨域策略

## 部署注意事项

### 生产环境配置

1. 修改默认密钥和密码
2. 使用更安全的数据库（如PostgreSQL、MySQL）
3. 配置反向代理（Nginx）
4. 启用HTTPS
5. 配置文件存储服务（如阿里云OSS）
6. 实施请求频率限制

### 示例Nginx配置

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    client_max_body_size 10M;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    location /uploads/ {
        alias /path/to/your/uploads/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
}
```

## 开发

### 添加新功能

1. 在 `app.py` 中添加新的路由
2. 定义相应的数据模型
3. 实现业务逻辑
4. 添加错误处理
5. 更新API文档

### 测试API

可以使用curl、Postman或其他API测试工具来测试接口：

```bash
# 登录获取token
curl -X POST http://localhost:9000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'

# 上传图片
curl -X POST http://localhost:9000/api/photos/upload \
  -H "Authorization: Bearer <your-token>" \
  -F "file=@/path/to/your/image.jpg" \
  -F "title=测试图片" \
  -F "description=这是一张测试图片"
```

### 生成测试图片

项目包含一个测试图片生成器，可以创建用于测试的示例图片：

```bash
# 生成测试图片
python create_test_image.py
```

这将在 `test_images/` 目录下创建多张不同尺寸的测试图片。

### 运行测试

项目提供了两种测试方式：

1. **内置测试客户端**（推荐）：
```bash
python simple_test.py
```

2. **HTTP请求测试**：
```bash
# 确保服务器在运行
python app.py &

# 运行测试
python test_api.py
```

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。 