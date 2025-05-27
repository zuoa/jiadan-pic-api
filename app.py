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
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:////data/photos.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-jwt-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 10485760))  # 10MB
app.config['VIEW_PASSWORD'] = os.getenv('VIEW_PASSWORD', '563538')  # 查看密钥
app.config['ADMIN_PASSWORD'] = os.getenv('ADMIN_PASSWORD', 'vaneljd')  # 查看密钥

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

def verify_view_access():
    """
    验证查看访问权限
    支持JWT Token或查看密钥两种方式
    返回: (is_authorized, access_type)
    """
    # 首先尝试JWT验证
    try:
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
        verify_jwt_in_request(optional=True)
        current_user_id = get_jwt_identity()
        if current_user_id:
            return True, 'user'
    except:
        pass
    
    # 然后尝试查看密钥验证
    view_password = request.headers.get('X-View-Password')
    print(view_password)

    if view_password and view_password == app.config['VIEW_PASSWORD']:
        return True, 'viewer'
    
    return False, 'public'

def get_file_size_string(size_bytes):
    """将字节数转换为可读的大小字符串"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

def generate_image_urls(photo, request_host=None):
    """
    为照片生成访问URL
    :param photo: 照片对象
    :param request_host: 请求的主机地址
    :return: 包含src和thumbnail的字典
    """
    # if not request_host:
    #     request_host = os.getenv("GALLERY_HOST", "/api/")
    #
    # base_url = f"http://{request_host}/api/images"
    #
    return {
        'src': f"/api/images/{photo.id}/original",
        'thumbnail': f"/api/images/{photo.id}/thumbnail"
    }

def format_photo_data(photo, request_host=None):
    """
    格式化照片数据，包含动态生成的URL
    """
    urls = generate_image_urls(photo, request_host)
    
    return {
        'id': photo.id,
        'title': photo.title,
        'description': photo.description,
        'src': urls['src'],
        'thumbnail': urls['thumbnail'],
        'date': photo.date,
        'size': photo.size,
        'location': photo.location,
        'is_public': photo.is_public,
        'file_name': photo.file_name,
        'mime_type': photo.mime_type,
        'created_at': photo.created_at.isoformat() if photo.created_at else None,
        'updated_at': photo.updated_at.isoformat() if photo.updated_at else None
    }

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
    title = db.Column(db.String(200), nullable=False, default='')
    description = db.Column(db.Text)
    src = db.Column(db.String(500), nullable=False)
    thumbnail = db.Column(db.String(500), nullable=False)
    date = db.Column(db.String(10))  # YYYY-MM-DD
    size = db.Column(db.Integer)  # 文件大小（字节）
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

# 图片访问命名空间
images_ns = Namespace('images', description='图片访问接口')
api.add_namespace(images_ns)

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

# 查看密钥验证模型
admin_verify_model = api.model('ViewKeyVerify', {
    'password': fields.String(required=True, description='查看密钥', example='admin-view-password-123')
})

# 修改密码模型
change_password_model = api.model('ChangePassword', {
    'current_password': fields.String(required=True, description='当前密码', example='oldpassword123'),
    'new_password': fields.String(required=True, description='新密码', example='newpassword123'),
    'confirm_password': fields.String(required=True, description='确认新密码', example='newpassword123')
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

# 修改密码响应模型
change_password_response_model = api.model('ChangePasswordResponse', {
    'success': fields.Boolean(description='请求是否成功', example=True),
    'message': fields.String(description='响应消息', example='密码修改成功')
})

# 照片相关模型
photo_model = api.model('Photo', {
    'id': fields.String(description='照片ID'),
    'title': fields.String(description='照片标题'),
    'description': fields.String(description='照片描述'),
    'src': fields.String(description='照片URL'),
    'thumbnail': fields.String(description='缩略图URL'),
    'date': fields.String(description='拍摄日期'),
    'size': fields.Integer(description='文件大小（字节）'),
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
class VerifyViewKey(Resource):
    @api.expect(admin_verify_model)
    @api.response(200, 'Success')
    @api.response(401, 'Unauthorized', error_model)
    @handle_errors
    def post(self):
        """验证查看密钥"""
        data = request.get_json()
        
        if not data or 'password' not in data:
            return {
                'success': False,
                'error': {
                    'code': 'MISSING_PASSWORD',
                    'message': '请提供查看密钥',
                    'details': '查看密钥是必需的'
                }
            }, 400
        
        view_password = app.config['VIEW_PASSWORD']
        
        if data['password'] == view_password:
            return {
                'success': True,
                'message': '查看密钥验证成功',
                'data': {
                    'access_type': 'viewer',
                    'permissions': ['view_all_photos'],
                    'can_view_private': True
                }
            }
        else:
            return {
                'success': False,
                'error': {
                    'code': 'INVALID_VIEW_KEY',
                    'message': '查看密钥错误',
                    'details': '请输入正确的查看密钥，验证失败只能查看公开图片'
                }
            }, 401

@auth_ns.route('/change-password')
class ChangePassword(Resource):
    @api.doc(security='Bearer')
    @api.expect(change_password_model)
    @api.response(200, 'Success', change_password_response_model)
    @api.response(400, 'Bad Request', error_model)
    @api.response(401, 'Unauthorized', error_model)
    @jwt_required()
    @handle_errors
    def post(self):
        """修改密码"""
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
        
        data = request.get_json()
        
        # 验证必需字段
        if not data or 'current_password' not in data or 'new_password' not in data or 'confirm_password' not in data:
            return {
                'success': False,
                'error': {
                    'code': 'MISSING_FIELDS',
                    'message': '缺少必需字段',
                    'details': '请提供当前密码、新密码和确认密码'
                }
            }, 400
        
        current_password = data['current_password']
        new_password = data['new_password']
        confirm_password = data['confirm_password']
        
        # 验证当前密码
        if not check_password_hash(user.password_hash, current_password):
            return {
                'success': False,
                'error': {
                    'code': 'INVALID_CURRENT_PASSWORD',
                    'message': '当前密码错误',
                    'details': '请输入正确的当前密码'
                }
            }, 400
        
        # 验证新密码长度
        if len(new_password) < 6:
            return {
                'success': False,
                'error': {
                    'code': 'PASSWORD_TOO_SHORT',
                    'message': '新密码太短',
                    'details': '密码长度至少为6位'
                }
            }, 400
        
        # 验证新密码确认
        if new_password != confirm_password:
            return {
                'success': False,
                'error': {
                    'code': 'PASSWORD_MISMATCH',
                    'message': '新密码确认不匹配',
                    'details': '新密码和确认密码必须一致'
                }
            }, 400
        
        # 检查新密码是否与当前密码相同
        if check_password_hash(user.password_hash, new_password):
            return {
                'success': False,
                'error': {
                    'code': 'SAME_PASSWORD',
                    'message': '新密码不能与当前密码相同',
                    'details': '请选择一个不同的新密码'
                }
            }, 400
        
        try:
            # 更新密码
            user.password_hash = generate_password_hash(new_password)
            user.updated_at = datetime.utcnow()
            db.session.commit()
            
            return {
                'success': True,
                'message': '密码修改成功'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': {
                    'code': 'PASSWORD_UPDATE_FAILED',
                    'message': '密码修改失败',
                    'details': str(e)
                }
            }, 500

# 照片管理接口
@photos_ns.route('')
class PhotoList(Resource):
    @api.doc(security='Bearer')
    @api.response(200, 'Success', photos_response_model)
    @api.param('page', '页码', type='integer', default=1)
    @api.param('per_page', '每页数量', type='integer', default=12)
    @api.param('search', '搜索关键词', type='string')
    @api.param('X-View-Password', '查看密钥（Header）', _in='header', type='string')
    @handle_errors
    def get(self):
        """获取照片列表（登录用户或提供查看密钥可查看所有照片，否则只能查看公开照片）"""
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 12, type=int), 100)
        search = request.args.get('search', '')
        
        # 验证访问权限
        is_authorized, access_type = verify_view_access()
        
        # 根据访问类型构建查询
        if access_type in ['viewer', 'user']:
            # 验证通过（查看密钥或登录用户），可以看到所有照片（包括非公开的）
            query = Photo.query
        else:
            # 验证失败，只能看到公开照片
            query = Photo.query.filter_by(is_public=True)
        
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
            photo_data = format_photo_data(photo)
            # 为查看者和登录用户添加额外信息
            if access_type in ['viewer', 'user']:
                photo_data['user_id'] = photo.user_id
                if photo.user:
                    photo_data['username'] = photo.user.username
            photos_data.append(photo_data)
        
        return {
            'success': True,
            'data': {
                'photos': photos_data,
                'pagination': {
                    'page': pagination.page,
                    'per_page': pagination.per_page,
                    'total': pagination.total,
                    'pages': pagination.pages
                },
                'access_type': access_type,
                'can_view_private': access_type in ['viewer', 'user']
            }
        }

@photos_ns.route('/<string:photo_id>')
class PhotoDetail(Resource):
    @api.doc(security='Bearer')
    @api.response(200, 'Success')
    @api.response(404, 'Not Found', error_model)
    @api.param('X-View-Password', '查看密钥（Header）', _in='header', type='string')
    @handle_errors
    def get(self, photo_id):
        """获取单张照片详情（登录用户或提供查看密钥可查看所有照片，否则只能查看公开照片）"""
        # 验证访问权限
        is_authorized, access_type = verify_view_access()
        
        # 根据访问类型查询照片
        if access_type in ['viewer', 'user']:
            # 验证通过（查看密钥或登录用户），可以查看所有照片
            photo = Photo.query.filter_by(id=photo_id).first()
        else:
            # 验证失败，只能查看公开照片
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
        
        photo_data = format_photo_data(photo)
        # 为查看者和登录用户添加额外信息
        if access_type in ['viewer', 'user']:
            photo_data['user_id'] = photo.user_id
            if photo.user:
                photo_data['username'] = photo.user.username
        
        return {
            'success': True,
            'data': {
                'photo': photo_data,
                'access_type': access_type,
                'can_view_private': access_type in ['viewer', 'user']
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
                    'photo': format_photo_data(photo)
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
            
            # 获取表单数据
            title = request.form.get('title', 'Unnamed')
            description = request.form.get('description', '')
            date = request.form.get('date', '')
            location = request.form.get('location', '')
            is_public = request.form.get('is_public', 'false').lower() == 'true'
            
            # 创建照片记录 - 不再存储直接URL，而是存储OSS key
            photo = Photo(
                title=title,
                description=description,
                src='',  # 将通过API动态生成
                thumbnail='',  # 将通过API动态生成
                date=date,
                size=upload_result['file_size'],  # 存储原始字节数
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
                    'photo': format_photo_data(photo)
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
            # 直接使用存储的文件大小
            if photo.size:
                total_size_bytes += photo.size
        
        total_size_str = get_file_size_string(total_size_bytes)
        
        # 获取最近上传的照片
        recent_photos = Photo.query.filter_by(user_id=int(current_user_id))\
                                  .order_by(Photo.created_at.desc())\
                                  .limit(5).all()
        
        recent_uploads = []
        for photo in recent_photos:
            recent_uploads.append(format_photo_data(photo))
        
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
            photos_data.append(format_photo_data(photo))
        
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
                'photo': format_photo_data(photo)
            }
        }

def _get_image(photo_id, image_type):
    """获取图片的通用方法"""
    from flask import Response
    
    photo = Photo.query.filter_by(id=photo_id).first()
    
    if not photo:
        return {
            'success': False,
            'error': {
                'code': 'PHOTO_NOT_FOUND',
                'message': '照片不存在',
                'details': '找不到指定的照片'
            }
        }, 404

    # 根据图片类型选择OSS key
    if image_type == 'thumbnail':
        file_key = photo.oss_thumbnail_key
    else:
        file_key = photo.oss_key
    
    if not file_key:
        return {
            'success': False,
            'error': {
                'code': 'FILE_NOT_FOUND',
                'message': '文件不存在',
                'details': '图片文件在存储中不存在'
            }
        }, 404
    
    try:
        if not oss_service:
            return {
                'success': False,
                'error': {
                    'code': 'OSS_UNAVAILABLE',
                    'message': 'OSS服务不可用',
                    'details': '图片存储服务暂时不可用'
                }
            }, 500

        
        # 生成临时签名URL并重定向
        signed_url = oss_service.generate_signed_url(file_key, expires_in_seconds=3600)  # 1小时过期
        return Response(status=302, headers={'Location': signed_url})
        
    except Exception as e:
        return {
            'success': False,
            'error': {
                'code': 'IMAGE_ACCESS_FAILED',
                'message': '图片访问失败',
                'details': str(e)
            }
        }, 500

# 图片访问接口
@images_ns.route('/<string:photo_id>/original')
class ImageOriginal(Resource):
    @api.doc(security='Bearer')
    @api.response(200, 'Success')
    @api.response(404, 'Not Found', error_model)
    @api.response(403, 'Forbidden', error_model)
    @api.param('X-View-Password', '查看密钥（Header）', _in='header', type='string')
    @handle_errors
    def get(self, photo_id):
        """获取原图（登录用户或提供查看密钥可访问私有图片）"""
        return _get_image(photo_id, 'original')

@images_ns.route('/<string:photo_id>/thumbnail')
class ImageThumbnail(Resource):
    @api.doc(security='Bearer')
    @api.response(200, 'Success')
    @api.response(404, 'Not Found', error_model)
    @api.response(403, 'Forbidden', error_model)
    @api.param('X-View-Password', '查看密钥（Header）', _in='header', type='string')
    @handle_errors
    def get(self, photo_id):
        """获取缩略图（登录用户或提供查看密钥可访问私有图片）"""
        return _get_image(photo_id, 'thumbnail')

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
                username='vane',
                email='admin@example.com',
                password_hash=generate_password_hash(app.config['ADMIN_PASSWORD'])
            )
            db.session.add(admin_user)
            db.session.commit()
            print(f'默认管理员账户创建成功: vane/{app.config["ADMIN_PASSWORD"]}')

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
    print("API文档地址: http://localhost:9000/api/docs/")
    print("默认账户: admin / admin123")
    app.run(debug=True, host='0.0.0.0', port=9000)
