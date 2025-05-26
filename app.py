from flask import Flask, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from flask_restx import Api, Resource, fields, Namespace
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from PIL import Image
import os
import uuid
import mimetypes
from dotenv import load_dotenv
from oss_service import oss_service

# 加载环境变量
load_dotenv()

app = Flask(__name__)

# 配置
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///photos.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-jwt-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 10485760))  # 10MB

# 初始化扩展
db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)

# 初始化 Flask-RESTX
api = Api(
    app,
    version='1.0',
    title='照片管理 API',
    description='一个功能完整的照片管理系统API，支持用户认证、照片上传、管理等功能',
    doc='/api/docs/',
    prefix='/api'
)

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_size_string(size_bytes):
    """将字节数转换为可读的大小字符串"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

# 数据模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    photos = db.relationship('Photo', backref='user', lazy=True, cascade='all, delete-orphan')

class Photo(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False, default='未命名照片')
    description = db.Column(db.Text)
    src = db.Column(db.String(500), nullable=False)
    thumbnail = db.Column(db.String(500), nullable=False)
    date = db.Column(db.String(10))  # YYYY-MM-DD
    size = db.Column(db.String(20))
    location = db.Column(db.String(200))
    is_public = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    file_name = db.Column(db.String(255))
    file_path = db.Column(db.String(500))  # 本地文件路径（兼容性保留）
    oss_key = db.Column(db.String(500))  # OSS文件key
    oss_thumbnail_key = db.Column(db.String(500))  # OSS缩略图key
    mime_type = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# API 模型定义
auth_ns = Namespace('auth', description='用户认证相关接口')
photos_ns = Namespace('photos', description='照片管理相关接口')
public_ns = Namespace('public', description='公开访问接口')
dashboard_ns = Namespace('dashboard', description='仪表板统计接口')

# 添加命名空间
api.add_namespace(auth_ns)
api.add_namespace(photos_ns)
api.add_namespace(public_ns)
api.add_namespace(dashboard_ns)

# 定义响应模型
error_model = api.model('Error', {
    'success': fields.Boolean(description='请求是否成功', example=False),
    'error': fields.Nested(api.model('ErrorDetail', {
        'code': fields.String(description='错误代码', example='INVALID_CREDENTIALS'),
        'message': fields.String(description='错误消息', example='用户名或密码错误'),
        'details': fields.String(description='错误详情', example='请检查您的登录凭据')
    }))
})

# 认证相关模型
login_model = api.model('Login', {
    'username': fields.String(required=True, description='用户名', example='admin'),
    'password': fields.String(required=True, description='密码', example='password123')
})

user_model = api.model('User', {
    'id': fields.Integer(description='用户ID'),
    'username': fields.String(description='用户名'),
    'email': fields.String(description='邮箱')
})

login_response_model = api.model('LoginResponse', {
    'success': fields.Boolean(description='请求是否成功', example=True),
    'message': fields.String(description='响应消息', example='登录成功'),
    'data': fields.Nested(api.model('LoginData', {
        'token': fields.String(description='JWT认证令牌'),
        'user': fields.Nested(user_model)
    }))
})

# 照片相关模型
photo_model = api.model('Photo', {
    'id': fields.String(description='照片ID'),
    'title': fields.String(description='照片标题'),
    'description': fields.String(description='照片描述'),
    'src': fields.String(description='照片URL'),
    'thumbnail': fields.String(description='缩略图URL'),
    'date': fields.String(description='拍摄日期'),
    'size': fields.String(description='文件大小'),
    'location': fields.String(description='拍摄地点'),
    'is_public': fields.Boolean(description='是否公开'),
    'file_name': fields.String(description='文件名'),
    'mime_type': fields.String(description='文件类型'),
    'created_at': fields.DateTime(description='创建时间'),
    'updated_at': fields.DateTime(description='更新时间')
})

photos_response_model = api.model('PhotosResponse', {
    'success': fields.Boolean(description='请求是否成功', example=True),
    'message': fields.String(description='响应消息'),
    'data': fields.Nested(api.model('PhotosData', {
        'photos': fields.List(fields.Nested(photo_model)),
        'pagination': fields.Nested(api.model('Pagination', {
            'page': fields.Integer(description='当前页码'),
            'per_page': fields.Integer(description='每页数量'),
            'total': fields.Integer(description='总数量'),
            'pages': fields.Integer(description='总页数')
        }))
    }))
})

photo_update_model = api.model('PhotoUpdate', {
    'title': fields.String(description='照片标题'),
    'description': fields.String(description='照片描述'),
    'date': fields.String(description='拍摄日期'),
    'location': fields.String(description='拍摄地点'),
    'is_public': fields.Boolean(description='是否公开')
})

# 仪表板统计模型
stats_model = api.model('DashboardStats', {
    'success': fields.Boolean(description='请求是否成功', example=True),
    'data': fields.Nested(api.model('StatsData', {
        'total_photos': fields.Integer(description='总照片数'),
        'public_photos': fields.Integer(description='公开照片数'),
        'private_photos': fields.Integer(description='私有照片数'),
        'total_size': fields.String(description='总文件大小'),
        'recent_uploads': fields.List(fields.Nested(photo_model), description='最近上传的照片')
    }))
})

# 错误处理装饰器
def handle_errors(f):
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return {
                'success': False,
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': '服务器内部错误',
                    'details': str(e)
                }
            }, 500
    return wrapper

# 认证接口
@auth_ns.route('/login')
class Login(Resource):
    @api.expect(login_model)
    @api.response(200, 'Success', login_response_model)
    @api.response(400, 'Bad Request', error_model)
    @api.response(401, 'Unauthorized', error_model)
    @handle_errors
    def post(self):
        """用户登录"""
        data = request.get_json()
        
        if not data or 'username' not in data or 'password' not in data:
            return {
                'success': False,
                'error': {
                    'code': 'MISSING_CREDENTIALS',
                    'message': '请提供用户名和密码',
                    'details': '用户名和密码都是必需的'
                }
            }, 400
        
        user = User.query.filter_by(username=data['username']).first()
        
        if user and check_password_hash(user.password_hash, data['password']):
            access_token = create_access_token(identity=str(user.id))
            return {
                'success': True,
                'message': '登录成功',
                'data': {
                    'token': access_token,
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email
                    }
                }
            }
        
        return {
            'success': False,
            'error': {
                'code': 'INVALID_CREDENTIALS',
                'message': '用户名或密码错误',
                'details': '请检查您的登录凭据'
            }
        }, 401

@auth_ns.route('/logout')
class Logout(Resource):
    @api.doc(security='Bearer')
    @api.response(200, 'Success')
    @jwt_required()
    @handle_errors
    def post(self):
        """用户登出"""
        return {
            'success': True,
            'message': '登出成功'
        }

@auth_ns.route('/verify')
class VerifyToken(Resource):
    @api.doc(security='Bearer')
    @api.response(200, 'Success')
    @api.response(401, 'Unauthorized', error_model)
    @jwt_required()
    @handle_errors
    def get(self):
        """验证token有效性"""
        current_user_id = get_jwt_identity()
        user = User.query.get(int(current_user_id))
        
        if not user:
            return {
                'success': False,
                'error': {
                    'code': 'USER_NOT_FOUND',
                    'message': '用户不存在',
                    'details': '找不到对应的用户'
                }
            }, 401
        
        return {
            'success': True,
            'data': {
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                }
            }
        }

# 照片管理接口
@photos_ns.route('')
class PhotoList(Resource):
    @api.doc(security='Bearer')
    @api.response(200, 'Success', photos_response_model)
    @api.param('page', '页码', type='integer', default=1)
    @api.param('per_page', '每页数量', type='integer', default=12)
    @api.param('search', '搜索关键词', type='string')
    @jwt_required()
    @handle_errors
    def get(self):
        """获取用户的照片列表"""
        current_user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 12, type=int), 100)
        search = request.args.get('search', '')
        
        query = Photo.query.filter_by(user_id=int(current_user_id))
        
        if search:
            query = query.filter(
                db.or_(
                    Photo.title.contains(search),
                    Photo.description.contains(search),
                    Photo.location.contains(search)
                )
            )
        
        query = query.order_by(Photo.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        photos_data = []
        for photo in pagination.items:
            photos_data.append({
                'id': photo.id,
                'title': photo.title,
                'description': photo.description,
                'src': photo.src,
                'thumbnail': photo.thumbnail,
                'date': photo.date,
                'size': photo.size,
                'location': photo.location,
                'is_public': photo.is_public,
                'file_name': photo.file_name,
                'mime_type': photo.mime_type,
                'created_at': photo.created_at.isoformat() if photo.created_at else None,
                'updated_at': photo.updated_at.isoformat() if photo.updated_at else None
            })
        
        return {
            'success': True,
            'data': {
                'photos': photos_data,
                'pagination': {
                    'page': pagination.page,
                    'per_page': pagination.per_page,
                    'total': pagination.total,
                    'pages': pagination.pages
                }
            }
        }

@photos_ns.route('/<string:photo_id>')
class PhotoDetail(Resource):
    @api.doc(security='Bearer')
    @api.response(200, 'Success')
    @api.response(404, 'Not Found', error_model)
    @jwt_required()
    @handle_errors
    def get(self, photo_id):
        """获取单张照片详情"""
        current_user_id = get_jwt_identity()
        photo = Photo.query.filter_by(id=photo_id, user_id=int(current_user_id)).first()
        
        if not photo:
            return {
                'success': False,
                'error': {
                    'code': 'PHOTO_NOT_FOUND',
                    'message': '照片不存在',
                    'details': '找不到指定的照片'
                }
            }, 404
        
        return {
            'success': True,
            'data': {
                'photo': {
                    'id': photo.id,
                    'title': photo.title,
                    'description': photo.description,
                    'src': photo.src,
                    'thumbnail': photo.thumbnail,
                    'date': photo.date,
                    'size': photo.size,
                    'location': photo.location,
                    'is_public': photo.is_public,
                    'file_name': photo.file_name,
                    'mime_type': photo.mime_type,
                    'created_at': photo.created_at.isoformat() if photo.created_at else None,
                    'updated_at': photo.updated_at.isoformat() if photo.updated_at else None
                }
            }
        }
    
    @api.doc(security='Bearer')
    @api.expect(photo_update_model)
    @api.response(200, 'Success')
    @api.response(404, 'Not Found', error_model)
    @jwt_required()
    @handle_errors
    def put(self, photo_id):
        """更新照片信息"""
        current_user_id = get_jwt_identity()
        photo = Photo.query.filter_by(id=photo_id, user_id=int(current_user_id)).first()
        
        if not photo:
            return {
                'success': False,
                'error': {
                    'code': 'PHOTO_NOT_FOUND',
                    'message': '照片不存在',
                    'details': '找不到指定的照片'
                }
            }, 404
        
        data = request.get_json()
        
        if 'title' in data:
            photo.title = data['title']
        if 'description' in data:
            photo.description = data['description']
        if 'date' in data:
            photo.date = data['date']
        if 'location' in data:
            photo.location = data['location']
        if 'is_public' in data:
            photo.is_public = data['is_public']
        
        photo.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            return {
                'success': True,
                'message': '照片信息更新成功',
                'data': {
                    'photo': {
                        'id': photo.id,
                        'title': photo.title,
                        'description': photo.description,
                        'src': photo.src,
                        'thumbnail': photo.thumbnail,
                        'date': photo.date,
                        'size': photo.size,
                        'location': photo.location,
                        'is_public': photo.is_public,
                        'file_name': photo.file_name,
                        'mime_type': photo.mime_type,
                        'created_at': photo.created_at.isoformat() if photo.created_at else None,
                        'updated_at': photo.updated_at.isoformat() if photo.updated_at else None
                    }
                }
            }
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': {
                    'code': 'UPDATE_FAILED',
                    'message': '更新照片信息失败',
                    'details': str(e)
                }
            }, 500
    
    @api.doc(security='Bearer')
    @api.response(200, 'Success')
    @api.response(404, 'Not Found', error_model)
    @jwt_required()
    @handle_errors
    def delete(self, photo_id):
        """删除照片"""
        current_user_id = get_jwt_identity()
        photo = Photo.query.filter_by(id=photo_id, user_id=int(current_user_id)).first()
        
        if not photo:
            return {
                'success': False,
                'error': {
                    'code': 'PHOTO_NOT_FOUND',
                    'message': '照片不存在',
                    'details': '找不到指定的照片'
                }
            }, 404
        
        try:
            # 删除OSS文件
            if oss_service and photo.oss_key:
                try:
                    oss_service.delete_image(photo.oss_key, photo.oss_thumbnail_key)
                except Exception as e:
                    print(f"删除OSS文件失败: {e}")
            
            # 删除本地文件（兼容性处理）
            if photo.file_path and os.path.exists(photo.file_path):
                os.remove(photo.file_path)
            
            # 删除本地缩略图
            thumbnail_path = photo.file_path.replace('uploads/', 'uploads/thumbnails/') if photo.file_path else None
            if thumbnail_path and os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
            
            db.session.delete(photo)
            db.session.commit()
            
            return {
                'success': True,
                'message': '照片删除成功'
            }
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': {
                    'code': 'DELETE_FAILED',
                    'message': '删除照片失败',
                    'details': str(e)
                }
            }, 500

@photos_ns.route('/upload')
class PhotoUpload(Resource):
    @api.doc(security='Bearer')
    @api.response(200, 'Success')
    @api.response(400, 'Bad Request', error_model)
    @api.response(413, 'File too large', error_model)
    @api.response(415, 'Unsupported media type', error_model)
    @jwt_required()
    @handle_errors
    def post(self):
        """上传照片"""
        current_user_id = get_jwt_identity()
        
        if 'file' not in request.files:
            return {
                'success': False,
                'error': {
                    'code': 'NO_FILE',
                    'message': '没有选择文件',
                    'details': '请选择要上传的图片文件'
                }
            }, 400
        
        file = request.files['file']
        
        if file.filename == '':
            return {
                'success': False,
                'error': {
                    'code': 'NO_FILE_SELECTED',
                    'message': '没有选择文件',
                    'details': '请选择要上传的图片文件'
                }
            }, 400
        
        if not allowed_file(file.filename):
            return {
                'success': False,
                'error': {
                    'code': 'INVALID_FILE_TYPE',
                    'message': '不支持的文件类型',
                    'details': '只支持 jpg, jpeg, png, gif, webp 格式的图片文件'
                }
            }, 415
        
        # 检查OSS服务是否可用
        if not oss_service:
            return {
                'success': False,
                'error': {
                    'code': 'OSS_UNAVAILABLE',
                    'message': 'OSS服务不可用',
                    'details': '请检查OSS配置'
                }
            }, 500
        
        try:
            # 生成唯一文件名
            file_ext = file.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4()}.{file_ext}"
            
            # 获取文件信息
            mime_type = mimetypes.guess_type(file.filename)[0] or 'image/jpeg'
            
            # 上传到OSS
            upload_result = oss_service.upload_image(file, unique_filename)
            
            file_size_str = get_file_size_string(upload_result['file_size'])
            
            # 获取表单数据
            title = request.form.get('title', '未命名照片')
            description = request.form.get('description', '')
            date = request.form.get('date', '')
            location = request.form.get('location', '')
            is_public = request.form.get('is_public', 'false').lower() == 'true'
            
            # 创建照片记录
            photo = Photo(
                title=title,
                description=description,
                src=upload_result['original_url'],
                thumbnail=upload_result['thumbnail_url'],
                date=date,
                size=file_size_str,
                location=location,
                is_public=is_public,
                user_id=int(current_user_id),
                file_name=file.filename,
                oss_key=upload_result['file_key'],
                oss_thumbnail_key=upload_result['thumbnail_key'],
                mime_type=mime_type
            )
            
            db.session.add(photo)
            db.session.commit()
            
            return {
                'success': True,
                'message': '照片上传成功',
                'data': {
                    'photo': {
                        'id': photo.id,
                        'title': photo.title,
                        'description': photo.description,
                        'src': photo.src,
                        'thumbnail': photo.thumbnail,
                        'date': photo.date,
                        'size': photo.size,
                        'location': photo.location,
                        'is_public': photo.is_public,
                        'file_name': photo.file_name,
                        'mime_type': photo.mime_type,
                        'created_at': photo.created_at.isoformat() if photo.created_at else None,
                        'updated_at': photo.updated_at.isoformat() if photo.updated_at else None
                    }
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': {
                    'code': 'UPLOAD_FAILED',
                    'message': '照片上传失败',
                    'details': str(e)
                }
            }, 500

# 仪表板统计接口
@dashboard_ns.route('/stats')
class DashboardStats(Resource):
    @api.doc(security='Bearer')
    @api.response(200, 'Success', stats_model)
    @jwt_required()
    @handle_errors
    def get(self):
        """获取仪表板统计信息"""
        current_user_id = get_jwt_identity()
        
        # 统计照片数量
        total_photos = Photo.query.filter_by(user_id=int(current_user_id)).count()
        public_photos = Photo.query.filter_by(user_id=int(current_user_id), is_public=True).count()
        private_photos = total_photos - public_photos
        
        # 计算总文件大小
        photos = Photo.query.filter_by(user_id=int(current_user_id)).all()
        total_size_bytes = 0
        for photo in photos:
            # 优先使用OSS文件信息
            if photo.oss_key and oss_service:
                try:
                    file_info = oss_service.get_file_info(photo.oss_key)
                    total_size_bytes += file_info['size']
                except:
                    # 如果获取OSS文件信息失败，尝试从本地文件获取
                    if photo.file_path and os.path.exists(photo.file_path):
                        total_size_bytes += os.path.getsize(photo.file_path)
            elif photo.file_path and os.path.exists(photo.file_path):
                total_size_bytes += os.path.getsize(photo.file_path)
        
        total_size_str = get_file_size_string(total_size_bytes)
        
        # 获取最近上传的照片
        recent_photos = Photo.query.filter_by(user_id=int(current_user_id))\
                                  .order_by(Photo.created_at.desc())\
                                  .limit(5).all()
        
        recent_uploads = []
        for photo in recent_photos:
            recent_uploads.append({
                'id': photo.id,
                'title': photo.title,
                'description': photo.description,
                'src': photo.src,
                'thumbnail': photo.thumbnail,
                'date': photo.date,
                'size': photo.size,
                'location': photo.location,
                'is_public': photo.is_public,
                'file_name': photo.file_name,
                'mime_type': photo.mime_type,
                'created_at': photo.created_at.isoformat() if photo.created_at else None,
                'updated_at': photo.updated_at.isoformat() if photo.updated_at else None
            })
        
        return {
            'success': True,
            'data': {
                'total_photos': total_photos,
                'public_photos': public_photos,
                'private_photos': private_photos,
                'total_size': total_size_str,
                'recent_uploads': recent_uploads
            }
        }

# 公开访问接口
@public_ns.route('/photos')
class PublicPhotoList(Resource):
    @api.response(200, 'Success', photos_response_model)
    @api.param('page', '页码', type='integer', default=1)
    @api.param('per_page', '每页数量', type='integer', default=12)
    @handle_errors
    def get(self):
        """获取公开照片列表"""
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 12, type=int), 100)
        
        query = Photo.query.filter_by(is_public=True).order_by(Photo.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        photos_data = []
        for photo in pagination.items:
            photos_data.append({
                'id': photo.id,
                'title': photo.title,
                'description': photo.description,
                'src': photo.src,
                'thumbnail': photo.thumbnail,
                'date': photo.date,
                'size': photo.size,
                'location': photo.location,
                'is_public': photo.is_public,
                'file_name': photo.file_name,
                'mime_type': photo.mime_type,
                'created_at': photo.created_at.isoformat() if photo.created_at else None,
                'updated_at': photo.updated_at.isoformat() if photo.updated_at else None
            })
        
        return {
            'success': True,
            'data': {
                'photos': photos_data,
                'pagination': {
                    'page': pagination.page,
                    'per_page': pagination.per_page,
                    'total': pagination.total,
                    'pages': pagination.pages
                }
            }
        }

@public_ns.route('/photos/<string:photo_id>')
class PublicPhotoDetail(Resource):
    @api.response(200, 'Success')
    @api.response(404, 'Not Found', error_model)
    @handle_errors
    def get(self, photo_id):
        """获取公开照片详情"""
        photo = Photo.query.filter_by(id=photo_id, is_public=True).first()
        
        if not photo:
            return {
                'success': False,
                'error': {
                    'code': 'PHOTO_NOT_FOUND',
                    'message': '照片不存在',
                    'details': '找不到指定的照片或照片未公开'
                }
            }, 404
        
        return {
            'success': True,
            'data': {
                'photo': {
                    'id': photo.id,
                    'title': photo.title,
                    'description': photo.description,
                    'src': photo.src,
                    'thumbnail': photo.thumbnail,
                    'date': photo.date,
                    'size': photo.size,
                    'location': photo.location,
                    'is_public': photo.is_public,
                    'file_name': photo.file_name,
                    'mime_type': photo.mime_type,
                    'created_at': photo.created_at.isoformat() if photo.created_at else None,
                    'updated_at': photo.updated_at.isoformat() if photo.updated_at else None
                }
            }
        }

# 文件服务路由
# 本地文件访问路由（兼容性保留，建议使用OSS）
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# 初始化数据库
def init_database():
    """初始化数据库"""
    with app.app_context():
        db.create_all()
        
        # 检查是否存在默认用户
        if not User.query.filter_by(username='admin').first():
            admin_user = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('admin123')
            )
            db.session.add(admin_user)
            db.session.commit()
            print('默认管理员账户创建成功: admin/admin123')

# JWT 错误处理
@app.errorhandler(422)
def handle_unprocessable_entity(e):
    return {
        'success': False,
        'error': {
            'code': 'TOKEN_INVALID',
            'message': 'Token无效',
            'details': 'JWT Token格式错误或已过期'
        }
    }, 422

# 配置 JWT 认证
api.authorizations = {
    'Bearer': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization',
        'description': 'JWT Authorization header using the Bearer scheme. Example: "Authorization: Bearer {token}"'
    }
}

# 自动初始化数据库
init_database()

if __name__ == '__main__':
    # 开发环境启动
    print("开发环境启动...")
    print("API文档地址: http://localhost:5000/api/docs/")
    print("默认账户: admin / admin123")
    app.run(debug=True, host='0.0.0.0', port=5000) 