from flask import Blueprint, jsonify
from app import db
from app.models import MLModel, Sample, User
from datetime import datetime
import redis
from config import Config

bp = Blueprint('health', __name__, url_prefix='/api/health')

@bp.route('/status', methods=['GET'])
def health_check():
    """系统健康检查接口"""
    status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'services': {}
    }
    
    # 检查数据库连接
    try:
        db.session.execute('SELECT 1')
        status['services']['database'] = 'healthy'
    except Exception as e:
        status['services']['database'] = f'unhealthy: {str(e)}'
        status['status'] = 'degraded'
    
    # 检查Redis连接
    try:
        redis_client = redis.from_url(Config.REDIS_URL)
        redis_client.ping()
        status['services']['redis'] = 'healthy'
    except Exception as e:
        status['services']['redis'] = f'unhealthy: {str(e)}'
        status['status'] = 'degraded'
    
    return jsonify(status), 200 if status['status'] == 'healthy' else 503

@bp.route('/stats', methods=['GET'])
def get_stats():
    """获取系统整体统计信息"""
    stats = {
        'total_users': User.query.count(),
        'total_samples': Sample.query.count(),
        'total_models': MLModel.query.count(),
        'active_models': MLModel.query.filter_by(is_active=True).count()
    }
    
    return jsonify(stats), 200

