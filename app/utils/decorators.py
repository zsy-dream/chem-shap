from functools import wraps
from flask import jsonify
from flask_login import current_user

def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': '未登录'}), 401
        
        if current_user.role != 'admin':
            return jsonify({'error': '需要管理员权限'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def validate_json(*expected_args):
    """JSON数据验证装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request
            
            if not request.is_json:
                return jsonify({'error': '请求必须是JSON格式'}), 400
            
            json_data = request.get_json()
            
            # 检查必需字段
            missing_fields = [field for field in expected_args if field not in json_data]
            if missing_fields:
                return jsonify({
                    'error': '缺少必需字段',
                    'missing_fields': missing_fields
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def handle_errors(f):
    """统一错误处理装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            return jsonify({'error': '参数错误', 'message': str(e)}), 400
        except FileNotFoundError as e:
            return jsonify({'error': '文件未找到', 'message': str(e)}), 404
        except PermissionError as e:
            return jsonify({'error': '权限不足', 'message': str(e)}), 403
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'error': '服务器内部错误', 'message': str(e)}), 500
    return decorated_function

