from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import db, login_manager
from app.models import User
from app.utils.decorators import validate_json, handle_errors
from app.utils.validators import UserRegisterSchema, UserLoginSchema
from pydantic import ValidationError

bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({'error': '未授权，请先登录'}), 401

@bp.route('/register', methods=['POST'])
@handle_errors
def register():
    """用户注册"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请求体不能为空'}), 400
    
    # 数据验证
    try:
        validated_data = UserRegisterSchema(**data)
    except ValidationError as e:
        return jsonify({'error': '数据验证失败', 'details': e.errors()}), 400
    
    # 检查用户名是否已存在
    if User.query.filter_by(username=validated_data.username).first():
        return jsonify({'error': '用户名已存在'}), 400
    
    # 创建用户
    user = User(username=validated_data.username, role=validated_data.role)
    user.set_password(validated_data.password)
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': '注册成功', 'user_id': user.id}), 201

@bp.route('/login', methods=['POST'])
@handle_errors
def login():
    """用户登录"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请求体不能为空'}), 400
    
    # 数据验证
    try:
        validated_data = UserLoginSchema(**data)
    except ValidationError as e:
        return jsonify({'error': '数据验证失败', 'details': e.errors()}), 400
    
    # 查找用户
    user = User.query.filter_by(username=validated_data.username).first()
    
    if user is None or not user.check_password(validated_data.password):
        return jsonify({'error': '用户名或密码错误'}), 401
    
    # 登录用户
    login_user(user, remember=True)
    
    return jsonify({
        'message': '登录成功',
        'user': {
            'id': user.id,
            'username': user.username,
            'role': user.role
        }
    }), 200

@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': '登出成功'}), 200

@bp.route('/current', methods=['GET'])
@login_required
def get_current_user():
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'role': current_user.role
    }), 200

@bp.route('/demo', methods=['POST'])
def demo_login():
    """演示账号登录"""
    user = User.query.filter_by(username='demo').first()
    if not user:
        user = User(username='demo', role='admin')
        user.set_password('demo123')
        db.session.add(user)
        db.session.commit()
    
    login_user(user, remember=True)
    
    return jsonify({
        'message': '演示登录成功',
        'user': {
            'id': user.id,
            'username': user.username,
            'role': user.role
        }
    }), 200

