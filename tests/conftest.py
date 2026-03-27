"""Pytest配置文件"""
import pytest
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import User

@pytest.fixture(scope='session')
def app():
    """创建测试应用（会话级别）"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    return app

@pytest.fixture(scope='function')
def client(app):
    """创建测试客户端（函数级别）"""
    with app.app_context():
        db.create_all()
        
        # 创建测试用户
        user = User(username='testuser', role='doctor')
        user.set_password('testpass123')
        db.session.add(user)
        
        admin = User(username='admin', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        
        db.session.commit()
        
        yield app.test_client()
        
        db.session.remove()
        db.drop_all()

