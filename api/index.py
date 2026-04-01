import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置环境变量
os.environ.setdefault('FLASK_ENV', 'production')

from unittest.mock import MagicMock

class MockMLModule(MagicMock):
    @classmethod
    def __getattr__(cls, name):
        return MagicMock()

# 针对Vercel演示环境的依赖阉割（防止体积超250MB导致崩溃）
heavy_modules = [
    'numpy', 'pandas', 'xgboost', 'lightgbm', 'shap', 'sklearn', 
    'sklearn.model_selection', 'sklearn.metrics', 'matplotlib', 
    'matplotlib.pyplot', 'seaborn', 'reportlab', 'scipy'
]
for mod in heavy_modules:
    sys.modules[mod] = MockMLModule()

from app import create_app

app = create_app()

# Vercel Serverless Handler
def handler(event, context):
    from flask import Flask, request
    from werkzeug.wrappers import Request, Response
    
    # 创建请求对象
    wsgi_input = event.get('body', '')
    if event.get('isBase64Encoded', False):
        import base64
        wsgi_input = base64.b64decode(wsgi_input)
    
    environ = {
        'REQUEST_METHOD': event.get('httpMethod', 'GET'),
        'SCRIPT_NAME': '',
        'PATH_INFO': event.get('path', '/'),
        'QUERY_STRING': event.get('queryStringParameters', {}),
        'SERVER_NAME': event.get('headers', {}).get('host', 'localhost'),
        'SERVER_PORT': event.get('headers', {}).get('x-forwarded-port', '80'),
        'HTTP_HOST': event.get('headers', {}).get('host', 'localhost'),
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': event.get('headers', {}).get('x-forwarded-proto', 'http'),
        'wsgi.input': type('BytesIO', (), {'read': lambda self, size: wsgi_input})(),
        'wsgi.errors': sys.stderr,
        'wsgi.multithread': True,
        'wsgi.multiprocess': True,
    }
    
    # 添加headers
    for key, value in event.get('headers', {}).items():
        key = key.upper().replace('-', '_')
        if key not in ('HTTP_HOST', 'CONTENT_TYPE', 'CONTENT_LENGTH'):
            environ[f'HTTP_{key}'] = value
    
    # 处理请求
    request = Request(environ)
    response = app.full_dispatch_request(request)
    
    # 构建响应
    return {
        'statusCode': response.status_code,
        'headers': dict(response.headers),
        'body': response.get_data(as_text=True)
    }
