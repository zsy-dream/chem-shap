import pytest
from app import create_app, db
from app.models import User

@pytest.fixture
def app():
    """创建测试应用"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()

def test_register(client):
    """测试用户注册"""
    response = client.post('/api/auth/register', json={
        'username': 'testuser',
        'password': 'testpass123',
        'role': 'doctor'
    })
    
    assert response.status_code == 201
    data = response.get_json()
    assert data['message'] == '注册成功'
    assert 'user_id' in data

def test_register_duplicate_username(client):
    """测试重复用户名注册"""
    # 第一次注册
    client.post('/api/auth/register', json={
        'username': 'testuser',
        'password': 'testpass123'
    })
    
    # 第二次注册相同用户名
    response = client.post('/api/auth/register', json={
        'username': 'testuser',
        'password': 'testpass456'
    })
    
    assert response.status_code == 400
    data = response.get_json()
    assert '用户名已存在' in data['error']

def test_login(client):
    """测试用户登录"""
    # 先注册
    client.post('/api/auth/register', json={
        'username': 'testuser',
        'password': 'testpass123'
    })
    
    # 登录
    response = client.post('/api/auth/login', json={
        'username': 'testuser',
        'password': 'testpass123'
    })
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == '登录成功'
    assert data['user']['username'] == 'testuser'

def test_login_wrong_password(client):
    """测试错误密码登录"""
    # 先注册
    client.post('/api/auth/register', json={
        'username': 'testuser',
        'password': 'testpass123'
    })
    
    # 使用错误密码登录
    response = client.post('/api/auth/login', json={
        'username': 'testuser',
        'password': 'wrongpass'
    })
    
    assert response.status_code == 401
    data = response.get_json()
    assert '用户名或密码错误' in data['error']

def test_logout(client):
    """测试用户登出"""
    # 注册并登录
    client.post('/api/auth/register', json={
        'username': 'testuser',
        'password': 'testpass123'
    })
    client.post('/api/auth/login', json={
        'username': 'testuser',
        'password': 'testpass123'
    })
    
    # 登出
    response = client.post('/api/auth/logout')
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == '登出成功'

