#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
贾丹照片管理系统 - OpenAPI版本启动文件
支持自动生成API文档和Swagger UI界面
"""

import os
import sys
import logging
from app_openapi import app, init_database

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server_openapi.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """启动应用主函数"""
    
    # 初始化数据库
    logger.info("正在初始化数据库...")
    init_database()
    logger.info("数据库初始化完成")
    
    # 设置服务器参数
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 9000))
    debug = os.getenv('DEBUG', 'true').lower() == 'true'
    
    logger.info(f"服务器配置:")
    logger.info(f"  地址: http://{host}:{port}")
    logger.info(f"  API文档: http://{host}:{port}/api/docs/")
    logger.info(f"  调试模式: {debug}")
    logger.info(f"  上传目录: {app.config['UPLOAD_FOLDER']}")
    
    print("\n" + "="*60)
    print("🚀 贾丹照片管理系统 - OpenAPI版本")
    print("="*60)
    print(f"📋 API文档地址: http://{host}:{port}/api/docs/")
    print(f"🌐 服务地址: http://{host}:{port}")
    print(f"👤 默认账户: admin / admin123")
    print("="*60 + "\n")
    
    try:
        # 启动服务器
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=debug,
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭服务器...")
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")
        sys.exit(1)
    finally:
        logger.info("服务器已关闭")

if __name__ == '__main__':
    main() 