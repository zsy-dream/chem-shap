import pytest
import os
from app import create_app, db
from app.models import User, Sample

@pytest.fixture
def app():
    """创建测试应用"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        
        # 创建测试用户
        user = User(username='testuser', role='researcher')
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()
        
        yield app
        
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()

@pytest.fixture
def auth_client(client):
    """创建已认证的测试客户端"""
    client.post('/api/auth/login', json={
        'username': 'testuser',
        'password': 'testpass123'
    })
    return client

def test_create_sample(auth_client):
    """测试创建样本"""
    response = auth_client.post('/api/data/samples', json={
        'sample_id': 'CHEM-001',
        'experiment_round': 1,
        'experiment_group': 'A'
    })
    
    assert response.status_code == 201
    data = response.get_json()
    assert data['message'] == '样本创建成功'

def test_get_samples(auth_client):
    """测试获取样本列表"""
    # 先创建样本
    auth_client.post('/api/data/samples', json={
        'sample_id': 'CHEM-001',
        'experiment_round': 1,
        'experiment_group': 'A'
    })
    
    # 获取列表
    response = auth_client.get('/api/data/samples')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) > 0

def test_health_check(client):
    """测试健康检查"""
    response = client.get('/api/health/status')
    assert response.status_code in [200, 503]
    data = response.get_json()
    assert 'status' in data
    assert 'services' in data


