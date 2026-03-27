import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///instance/shap_chemistry.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_POOL_RECYCLE = 3600
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    UPLOAD_FOLDER = 'uploads'
    MODEL_FOLDER = 'models'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # CORS配置
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # 缓存配置
    CACHE_DEFAULT_TIMEOUT = 3600  # 1小时
    SHAP_CACHE_TIMEOUT = 7200  # 2小时
    
    # 速率限制
    RATELIMIT_ENABLED = os.environ.get('RATELIMIT_ENABLED', 'True') == 'True'
    RATELIMIT_DEFAULT = "100 per hour"
    # 华为云 ModelArts MaaS API (OpenAI 兼容)
    MAAS_ENDPOINT = os.environ.get('MAAS_ENDPOINT', 'https://api.modelarts-maas.com/v2/chat/completions')
    MAAS_API_KEY = os.environ.get('MAAS_API_KEY')
    MAAS_MODEL = os.environ.get('MAAS_MODEL', 'deepseek-v3.2')

