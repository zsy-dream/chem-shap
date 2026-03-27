from flask import jsonify
from typing import Any, Dict, Optional

def success_response(data: Any = None, message: str = "操作成功", code: int = 200):
    """成功响应"""
    response = {
        'success': True,
        'message': message,
        'code': code
    }
    if data is not None:
        response['data'] = data
    return jsonify(response), code

def error_response(message: str, code: int = 400, details: Optional[Any] = None):
    """错误响应"""
    response = {
        'success': False,
        'error': message,
        'code': code
    }
    if details is not None:
        response['details'] = details
    return jsonify(response), code

def paginated_response(items: list, page: int, per_page: int, total: int):
    """分页响应"""
    return jsonify({
        'success': True,
        'data': items,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
    }), 200

