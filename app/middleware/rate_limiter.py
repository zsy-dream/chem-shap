from flask import request, jsonify
from functools import wraps
import redis
import time
from config import Config

redis_client = redis.from_url(Config.REDIS_URL, decode_responses=True)

def rate_limit(max_requests=100, window=3600):
    """速率限制装饰器
    
    Args:
        max_requests: 时间窗口内最大请求数
        window: 时间窗口（秒）
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not Config.RATELIMIT_ENABLED:
                return f(*args, **kwargs)
            
            # 获取客户端标识（IP地址）
            client_id = request.remote_addr
            key = f"rate_limit:{f.__name__}:{client_id}"
            
            try:
                # 获取当前请求次数
                current = redis_client.get(key)
                
                if current is None:
                    # 首次请求
                    redis_client.setex(key, window, 1)
                elif int(current) >= max_requests:
                    # 超过限制
                    return jsonify({
                        'error': '请求过于频繁，请稍后再试',
                        'retry_after': redis_client.ttl(key)
                    }), 429
                else:
                    # 增加计数
                    redis_client.incr(key)
                
                return f(*args, **kwargs)
            except redis.RedisError:
                # Redis连接失败，允许请求通过
                return f(*args, **kwargs)
        
        return decorated_function
    return decorator

