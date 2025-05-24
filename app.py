from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from PIL import Image
import os
import uuid
import mimetypes
from dotenv import load_dotenv

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
    file_path = db.Column(db.String(500))
    mime_type = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 错误处理
@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        'success': False,
        'error': {
            'code': 'BAD_REQUEST',
            'message': '请求参数错误',
            'details': str(error.description)
        }
    }), 400

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({
        'success': False,
        'error': {
            'code': 'UNAUTHORIZED',
            'message': '未认证',
            'details': '请提供有效的认证令牌'
        }
    }), 401

@app.errorhandler(403)
def forbidden(error):
    return jsonify({
        'success': False,
        'error': {
            'code': 'FORBIDDEN',
            'message': '无权限',
            'details': '您没有访问此资源的权限'
        }
    }), 403

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': {
            'code': 'NOT_FOUND',
            'message': '资源不存在',
            'details': '请求的资源未找到'
        }
    }), 404

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        'success': False,
        'error': {
            'code': 'FILE_TOO_LARGE',
            'message': '文件过大',
            'details': '文件大小不能超过10MB'
        }
    }), 413

@app.errorhandler(415)
def unsupported_media_type(error):
    return jsonify({
        'success': False,
        'error': {
            'code': 'INVALID_FILE_TYPE',
            'message': '不支持的文件类型',
            'details': '只支持 jpg, jpeg, png, gif, webp 格式的图片文件'
        }
    }), 415

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({
        'success': False,
        'error': {
            'code': 'INTERNAL_ERROR',
            'message': '服务器内部错误',
            'details': '服务器处理请求时出现错误'
        }
    }), 500

# 认证接口
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({
            'success': False,
            'error': {
                'code': 'MISSING_CREDENTIALS',
                'message': '请提供用户名和密码',
                'details': '用户名和密码都是必需的'
            }
        }), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if user and check_password_hash(user.password_hash, data['password']):
        access_token = create_access_token(identity=str(user.id))
        return jsonify({
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
        })
    
    return jsonify({
        'success': False,
        'error': {
            'code': 'INVALID_CREDENTIALS',
            'message': '用户名或密码错误',
            'details': '请检查您的登录凭据'
        }
    }), 401

@app.route('/api/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    return jsonify({
        'success': True,
        'message': '退出登录成功'
    })

@app.route('/api/auth/verify', methods=['GET'])
@jwt_required()
def verify_token():
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({
            'success': False,
            'error': {
                'code': 'USER_NOT_FOUND',
                'message': '用户不存在',
                'details': '令牌对应的用户已被删除'
            }
        }), 404
    
    return jsonify({
        'success': True,
        'data': {
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        }
    })

# 照片管理接口
@app.route('/api/photos', methods=['GET'])
@jwt_required()
def get_photos():
    current_user_id = int(get_jwt_identity())
    
    # 获取查询参数
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)
    sort = request.args.get('sort', 'date')
    order = request.args.get('order', 'desc')
    public_only = request.args.get('public_only', 'false').lower() == 'true'
    
    # 构建查询
    query = Photo.query
    
    if public_only:
        query = query.filter_by(is_public=True)
    else:
        query = query.filter_by(user_id=current_user_id)
    
    # 排序
    if sort == 'date':
        if order == 'desc':
            query = query.order_by(Photo.date.desc())
        else:
            query = query.order_by(Photo.date.asc())
    elif sort == 'title':
        if order == 'desc':
            query = query.order_by(Photo.title.desc())
        else:
            query = query.order_by(Photo.title.asc())
    elif sort == 'size':
        if order == 'desc':
            query = query.order_by(Photo.size.desc())
        else:
            query = query.order_by(Photo.size.asc())
    
    # 分页
    pagination = query.paginate(page=page, per_page=size, error_out=False)
    photos = pagination.items
    
    return jsonify({
        'success': True,
        'data': {
            'photos': [{
                'id': photo.id,
                'title': photo.title,
                'description': photo.description,
                'src': photo.src,
                'thumbnail': photo.thumbnail,
                'date': photo.date,
                'size': photo.size,
                'location': photo.location,
                'isPublic': photo.is_public,
                'created_at': photo.created_at.isoformat() + 'Z'
            } for photo in photos],
            'pagination': {
                'page': page,
                'size': size,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }
    })

@app.route('/api/photos/<photo_id>', methods=['GET'])
@jwt_required()
def get_photo(photo_id):
    current_user_id = int(get_jwt_identity())
    photo = Photo.query.filter_by(id=photo_id, user_id=current_user_id).first()
    
    if not photo:
        return jsonify({
            'success': False,
            'error': {
                'code': 'PHOTO_NOT_FOUND',
                'message': '照片不存在',
                'details': '请求的照片未找到或您没有访问权限'
            }
        }), 404
    
    return jsonify({
        'success': True,
        'data': {
            'id': photo.id,
            'title': photo.title,
            'description': photo.description,
            'src': photo.src,
            'thumbnail': photo.thumbnail,
            'date': photo.date,
            'size': photo.size,
            'location': photo.location,
            'isPublic': photo.is_public,
            'created_at': photo.created_at.isoformat() + 'Z',
            'updated_at': photo.updated_at.isoformat() + 'Z'
        }
    })

@app.route('/api/photos/upload', methods=['POST'])
@jwt_required()
def upload_photo():
    current_user_id = int(get_jwt_identity())
    
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': {
                'code': 'NO_FILE',
                'message': '没有文件',
                'details': '请选择要上传的图片文件'
            }
        }), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            'success': False,
            'error': {
                'code': 'NO_FILE',
                'message': '没有文件',
                'details': '请选择要上传的图片文件'
            }
        }), 400
    
    if not allowed_file(file.filename):
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_FILE_TYPE',
                'message': '不支持的文件类型',
                'details': '只支持 jpg, jpeg, png, gif, webp 格式的图片文件'
            }
        }), 415
    
    # 生成唯一的照片ID
    photo_id = str(uuid.uuid4())
    
    # 创建照片目录
    photo_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'photos', photo_id)
    os.makedirs(photo_dir, exist_ok=True)
    
    # 保存原图
    filename = secure_filename(file.filename)
    file_ext = filename.rsplit('.', 1)[1].lower()
    original_filename = f"original.{file_ext}"
    original_path = os.path.join(photo_dir, original_filename)
    file.save(original_path)
    
    # 获取文件信息
    file_size = os.path.getsize(original_path)
    mime_type = mimetypes.guess_type(original_path)[0]
    
    # 生成缩略图
    try:
        with Image.open(original_path) as img:
            # 缩略图尺寸
            thumbnail_size = (300, 200)
            img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
            
            thumbnail_filename = f"thumbnail.{file_ext}"
            thumbnail_path = os.path.join(photo_dir, thumbnail_filename)
            img.save(thumbnail_path)
    except Exception as e:
        # 如果生成缩略图失败，删除已上传的文件
        if os.path.exists(original_path):
            os.remove(original_path)
        return jsonify({
            'success': False,
            'error': {
                'code': 'THUMBNAIL_GENERATION_FAILED',
                'message': '缩略图生成失败',
                'details': f'处理图片时出现错误: {str(e)}'
            }
        }), 500
    
    # 获取表单数据
    title = request.form.get('title', '未命名照片')
    description = request.form.get('description', '')
    location = request.form.get('location', '')
    date = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
    is_public = request.form.get('isPublic', 'false').lower() == 'true'
    
    # 创建照片记录
    photo = Photo(
        id=photo_id,
        title=title,
        description=description,
        src=f"/uploads/photos/{photo_id}/{original_filename}",
        thumbnail=f"/uploads/photos/{photo_id}/{thumbnail_filename}",
        date=date,
        size=get_file_size_string(file_size),
        location=location,
        is_public=is_public,
        user_id=current_user_id,
        file_name=filename,
        file_path=original_path,
        mime_type=mime_type
    )
    
    db.session.add(photo)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '照片上传成功',
        'data': {
            'id': photo.id,
            'title': photo.title,
            'description': photo.description,
            'src': photo.src,
            'thumbnail': photo.thumbnail,
            'date': photo.date,
            'size': photo.size,
            'location': photo.location,
            'isPublic': photo.is_public,
            'created_at': photo.created_at.isoformat() + 'Z'
        }
    })

@app.route('/api/photos/<photo_id>', methods=['PUT'])
@jwt_required()
def update_photo(photo_id):
    current_user_id = int(get_jwt_identity())
    photo = Photo.query.filter_by(id=photo_id, user_id=current_user_id).first()
    
    if not photo:
        return jsonify({
            'success': False,
            'error': {
                'code': 'PHOTO_NOT_FOUND',
                'message': '照片不存在',
                'details': '请求的照片未找到或您没有访问权限'
            }
        }), 404
    
    data = request.get_json()
    if not data:
        return jsonify({
            'success': False,
            'error': {
                'code': 'NO_DATA',
                'message': '没有数据',
                'details': '请提供要更新的数据'
            }
        }), 400
    
    # 更新字段
    if 'title' in data:
        photo.title = data['title']
    if 'description' in data:
        photo.description = data['description']
    if 'location' in data:
        photo.location = data['location']
    if 'date' in data:
        photo.date = data['date']
    if 'isPublic' in data:
        photo.is_public = data['isPublic']
    
    photo.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '照片信息更新成功',
        'data': {
            'id': photo.id,
            'title': photo.title,
            'description': photo.description,
            'src': photo.src,
            'thumbnail': photo.thumbnail,
            'date': photo.date,
            'size': photo.size,
            'location': photo.location,
            'isPublic': photo.is_public,
            'updated_at': photo.updated_at.isoformat() + 'Z'
        }
    })

@app.route('/api/photos/<photo_id>', methods=['DELETE'])
@jwt_required()
def delete_photo(photo_id):
    current_user_id = int(get_jwt_identity())
    photo = Photo.query.filter_by(id=photo_id, user_id=current_user_id).first()
    
    if not photo:
        return jsonify({
            'success': False,
            'error': {
                'code': 'PHOTO_NOT_FOUND',
                'message': '照片不存在',
                'details': '请求的照片未找到或您没有访问权限'
            }
        }), 404
    
    # 删除文件
    photo_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'photos', photo_id)
    if os.path.exists(photo_dir):
        import shutil
        shutil.rmtree(photo_dir)
    
    # 删除数据库记录
    db.session.delete(photo)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '照片删除成功'
    })

# 统计接口
@app.route('/api/dashboard/stats', methods=['GET'])
@jwt_required()
def dashboard_stats():
    current_user_id = int(get_jwt_identity())
    
    # 总照片数
    total_photos = Photo.query.filter_by(user_id=current_user_id).count()
    
    # 公开和私有照片数
    public_photos = Photo.query.filter_by(user_id=current_user_id, is_public=True).count()
    private_photos = total_photos - public_photos
    
    # 本月上传的照片数
    current_month = datetime.now().strftime('%Y-%m')
    this_month = Photo.query.filter(
        Photo.user_id == current_user_id,
        Photo.created_at >= datetime.strptime(current_month + '-01', '%Y-%m-%d')
    ).count()
    
    # 计算总存储大小
    user_photos = Photo.query.filter_by(user_id=current_user_id).all()
    total_size_bytes = 0
    for photo in user_photos:
        if os.path.exists(photo.file_path):
            total_size_bytes += os.path.getsize(photo.file_path)
    
    total_size = get_file_size_string(total_size_bytes)
    storage_limit = "1 GB"  # 假设的存储限制
    
    return jsonify({
        'success': True,
        'data': {
            'totalPhotos': total_photos,
            'totalSize': total_size,
            'thisMonth': this_month,
            'publicPhotos': public_photos,
            'privatePhotos': private_photos,
            'storageUsed': total_size,
            'storageLimit': storage_limit
        }
    })

# 公开接口
@app.route('/api/public/photos', methods=['GET'])
def get_public_photos():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 12, type=int)
    
    pagination = Photo.query.filter_by(is_public=True).order_by(Photo.created_at.desc()).paginate(
        page=page, per_page=size, error_out=False
    )
    photos = pagination.items
    
    return jsonify({
        'success': True,
        'data': {
            'photos': [{
                'id': photo.id,
                'title': photo.title,
                'description': photo.description,
                'src': photo.src,
                'thumbnail': photo.thumbnail,
                'date': photo.date,
                'location': photo.location
            } for photo in photos],
            'pagination': {
                'page': page,
                'size': size,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }
    })

@app.route('/api/public/photos/<photo_id>', methods=['GET'])
def get_public_photo(photo_id):
    photo = Photo.query.filter_by(id=photo_id, is_public=True).first()
    
    if not photo:
        return jsonify({
            'success': False,
            'error': {
                'code': 'PHOTO_NOT_FOUND',
                'message': '照片不存在',
                'details': '请求的公开照片未找到'
            }
        }), 404
    
    return jsonify({
        'success': True,
        'data': {
            'id': photo.id,
            'title': photo.title,
            'description': photo.description,
            'src': photo.src,
            'thumbnail': photo.thumbnail,
            'date': photo.date,
            'location': photo.location
        }
    })

# 静态文件服务
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# 初始化数据库和创建默认用户
def init_database():
    """初始化数据库和创建默认用户"""
    with app.app_context():
        db.create_all()
        
        # 创建默认管理员用户
        if not User.query.filter_by(username='admin').first():
            admin_user = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('password')
            )
            db.session.add(admin_user)
            db.session.commit()
            print("默认管理员用户已创建: username=admin, password=password")

if __name__ == '__main__':
    init_database()
    app.run(debug=True, host='0.0.0.0', port=9000) 