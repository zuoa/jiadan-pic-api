# 贾丹照片管理 API

一个基于 Flask 的照片管理系统 API，支持用户认证、照片上传、管理等功能，使用阿里云 OSS 进行文件存储。

## 主要功能

- 🔐 用户认证（JWT）
- 📸 照片上传（支持多种格式）
- 🗂️ 照片管理（增删改查）
- 🌐 公开照片分享
- 📊 仪表板统计
- ☁️ 阿里云 OSS 存储
- 🔑 管理员密码访问（无需登录查看所有照片）
- 📖 完整的 OpenAPI 文档

## 技术栈

- **后端框架**: Flask + Flask-RESTX
- **数据库**: SQLAlchemy（支持 SQLite/MySQL/PostgreSQL）
- **认证**: JWT
- **文件存储**: 阿里云 OSS
- **图片处理**: Pillow
- **API 文档**: OpenAPI/Swagger

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `env.example` 为 `.env` 并配置：

```bash
cp env.example .env
```

编辑 `.env` 文件，配置阿里云 OSS 信息和管理员密码：

```env
# 管理员查看密码（用于无需登录查看所有照片）
ADMIN_ACCESS_PASSWORD=your-admin-password-here

# 阿里云OSS配置
ALIYUN_ACCESS_KEY_ID=your-access-key-id
ALIYUN_ACCESS_KEY_SECRET=your-access-key-secret
ALIYUN_OSS_ENDPOINT=https://oss-cn-hangzhou.aliyuncs.com
ALIYUN_OSS_BUCKET=your-bucket-name
```

### 3. 运行应用

**开发环境：**
```bash
python app.py
```

**生产环境：**
```bash
# 使用配置文件启动
gunicorn -c gunicorn.conf.py app:app

# 或者直接指定参数
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

应用将在 `http://localhost:5000` 启动。

### 4. 访问 API 文档

打开浏览器访问：`http://localhost:5000/api/docs/`

## API 接口

### 认证接口

- `POST /api/auth/login` - 用户登录
- `POST /api/auth/logout` - 用户登出
- `GET /api/auth/verify` - 验证 token
- `POST /api/auth/verify` - 验证管理员密码

### 照片管理接口

- `GET /api/photos` - 获取照片列表（支持管理员密码访问）
- `POST /api/photos/upload` - 上传照片
- `GET /api/photos/{id}` - 获取照片详情（支持管理员密码访问）
- `PUT /api/photos/{id}` - 更新照片信息
- `DELETE /api/photos/{id}` - 删除照片

### 公开接口

- `GET /api/public/photos` - 获取公开照片列表
- `GET /api/public/photos/{id}` - 获取公开照片详情

### 仪表板接口

- `GET /api/dashboard/stats` - 获取统计信息

## 默认账户

- 用户名: `admin`
- 密码: `admin123`

## 管理员密码访问

系统支持通过管理员密码来访问所有照片（包括私有照片），无需用户登录。

### 使用方法

1. **在请求头中添加管理员密码：**
   ```
   X-Admin-Password: your-admin-password-here
   ```

2. **或者通过验证接口：**
   ```bash
   POST /api/auth/verify
   {
       "password": "your-admin-password-here"
   }
   ```

详细使用说明请参考：[管理员密码访问功能使用指南](ADMIN_ACCESS_GUIDE.md)

## 支持的图片格式

- JPG/JPEG
- PNG
- GIF
- WebP

## 文件存储

系统使用阿里云 OSS 进行文件存储，支持：

- 自动生成缩略图
- 文件去重
- 高可用性存储
- CDN 加速访问

## 开发说明

### 项目结构

```
├── app.py              # 主应用文件
├── oss_service.py      # OSS 服务模块
├── requirements.txt    # 依赖包
├── gunicorn.conf.py    # Gunicorn 配置文件
├── env.example        # 环境变量示例
├── README.md          # 说明文档
└── .gitignore         # Git 忽略文件
```

### 数据库模型

- `User`: 用户模型
- `Photo`: 照片模型（包含 OSS 存储字段）

## 部署

### 生产环境部署步骤

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **配置环境变量**
   ```bash
   cp env.example .env
   # 编辑 .env 文件，配置生产环境参数
   ```

3. **配置阿里云 OSS**
   在 `.env` 文件中设置：
   ```env
   ALIYUN_ACCESS_KEY_ID=your-production-key
   ALIYUN_ACCESS_KEY_SECRET=your-production-secret
   ALIYUN_OSS_ENDPOINT=https://oss-cn-hangzhou.aliyuncs.com
   ALIYUN_OSS_BUCKET=your-production-bucket
   ```

4. **启动服务**
   ```bash
   # 使用 Gunicorn 配置文件
   gunicorn -c gunicorn.conf.py app:app
   
   # 或者后台运行
   nohup gunicorn -c gunicorn.conf.py app:app > app.log 2>&1 &
   ```

### Docker 部署（可选）

创建 `Dockerfile`：
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
```

构建和运行：
```bash
docker build -t jiadan-pic-api .
docker run -d -p 5000:5000 --env-file .env jiadan-pic-api
```

## 许可证

MIT License 