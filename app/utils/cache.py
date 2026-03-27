import redis
import json
import pickle
from functools import wraps
from config import Config

class CacheService:
    def __init__(self):
        self.redis_client = redis.from_url(Config.REDIS_URL, decode_responses=False)
    
    def get(self, key):
        """获取缓存"""
        try:
            data = self.redis_client.get(key)
            if data:
                return pickle.loads(data)
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    def set(self, key, value, expire=3600):
        """设置缓存"""
        try:
            self.redis_client.setex(key, expire, pickle.dumps(value))
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    def delete(self, key):
        """删除缓存"""
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    def clear_pattern(self, pattern):
        """清除匹配模式的所有缓存"""
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
            return True
        except Exception as e:
            print(f"Cache clear error: {e}")
            return False

def cache_result(expire=3600, key_prefix=''):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = CacheService()
            
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # 尝试从缓存获取
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return cached_data
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存入缓存
            cache.set(cache_key, result, expire)
            
            return result
        return wrapper
    return decorator

