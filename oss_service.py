import os
import uuid
import oss2
from PIL import Image
import io
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class OSSService:
    def __init__(self):
        # 阿里云OSS配置
        self.access_key_id = os.getenv('ALIYUN_ACCESS_KEY_ID')
        self.access_key_secret = os.getenv('ALIYUN_ACCESS_KEY_SECRET')
        self.endpoint = os.getenv('ALIYUN_OSS_ENDPOINT')
        self.bucket_name = os.getenv('ALIYUN_OSS_BUCKET')
        
        if not all([self.access_key_id, self.access_key_secret, self.endpoint, self.bucket_name]):
            raise ValueError("阿里云OSS配置不完整，请检查环境变量")
        
        # 创建OSS认证和bucket对象
        auth = oss2.Auth(self.access_key_id, self.access_key_secret)
        self.bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
    
    def upload_image(self, file_obj, filename=None):
        """
        上传图片到OSS
        :param file_obj: 文件对象
        :param filename: 文件名（可选）
        :return: 文件信息字典
        """
        try:
            # 生成唯一文件名
            if not filename:
                filename = f"{uuid.uuid4()}.jpg"
            
            # 确保文件名有正确的扩展名
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                filename = f"{filename}.jpg"
            
            # 读取文件内容
            file_obj.seek(0)
            file_content = file_obj.read()
            file_size = len(file_content)
            
            # 生成文件路径
            original_key = f"photos/{filename}"
            thumbnail_key = f"thumbnails/{filename}"
            
            # 上传原图
            result = self.bucket.put_object(original_key, file_content)
            
            # 创建缩略图
            file_obj.seek(0)
            thumbnail_content = self._create_thumbnail(file_obj)
            
            # 上传缩略图
            self.bucket.put_object(thumbnail_key, thumbnail_content)
            
            return {
                'file_size': file_size,
                'file_key': original_key,
                'thumbnail_key': thumbnail_key
            }
            
        except Exception as e:
            raise Exception(f"上传文件到OSS失败: {str(e)}")
    
    def generate_signed_url(self, file_key, expires_in_seconds=3600):
        """
        生成OSS文件的签名URL
        :param file_key: 文件key
        :param expires_in_seconds: 过期时间（秒），默认1小时
        :return: 签名URL
        """
        try:
            # 生成签名URL
            url = self.bucket.sign_url('GET', file_key, expires_in_seconds)
            return url
        except Exception as e:
            raise Exception(f"生成签名URL失败: {str(e)}")
    
    def generate_public_url(self, file_key):
        """
        生成公开访问的URL（仅用于公开图片）
        注意：这种方式仍然暴露永久URL，建议仅对公开图片使用
        :param file_key: 文件key
        :return: 公开URL
        """
        return f"https://{self.bucket_name}.{self.endpoint.replace('https://', '')}/{file_key}"
    
    def get_image_stream(self, file_key):
        """
        直接获取图片文件流
        :param file_key: 文件key
        :return: 文件流
        """
        try:
            result = self.bucket.get_object(file_key)
            return result
        except Exception as e:
            raise Exception(f"获取文件流失败: {str(e)}")
    
    def delete_image(self, file_key, thumbnail_key=None):
        """
        删除OSS中的图片
        :param file_key: 原图文件key
        :param thumbnail_key: 缩略图文件key
        """
        try:
            # 删除原图
            self.bucket.delete_object(file_key)
            
            # 删除缩略图
            if thumbnail_key:
                self.bucket.delete_object(thumbnail_key)
                
        except Exception as e:
            raise Exception(f"删除OSS文件失败: {str(e)}")
    
    def _create_thumbnail(self, file_obj, size=(300, 300)):
        """
        创建缩略图
        :param file_obj: 文件对象
        :param size: 缩略图尺寸
        :return: 缩略图字节数据
        """
        try:
            # 打开图片
            image = Image.open(file_obj)
            
            # 转换为RGB模式（处理RGBA等格式）
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
            # 创建缩略图
            image.thumbnail(size, Image.Resampling.LANCZOS)
            
            # 保存到字节流
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=85)
            output.seek(0)
            
            return output.getvalue()
            
        except Exception as e:
            raise Exception(f"创建缩略图失败: {str(e)}")
    
    def get_file_info(self, file_key):
        """
        获取OSS文件信息
        :param file_key: 文件key
        :return: 文件信息
        """
        try:
            result = self.bucket.head_object(file_key)
            return {
                'size': result.content_length,
                'last_modified': result.last_modified,
                'content_type': result.content_type
            }
        except Exception as e:
            raise Exception(f"获取文件信息失败: {str(e)}")

# 创建全局OSS服务实例
try:
    oss_service = OSSService()
except ValueError as e:
    print(f"警告: {e}")
    oss_service = None 