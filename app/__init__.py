import matplotlib
matplotlib.use('Agg')

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 启用CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'web.login'
    
    # 配置日志（Vercel 只读文件系统，禁用文件日志）
    # from app.utils.logger import setup_logger
    # setup_logger(app)
    
    # 注册蓝图
    from app.routes import auth, data, model, analysis, report, health, web
    app.register_blueprint(auth.bp)
    app.register_blueprint(data.bp)
    app.register_blueprint(model.bp)
    app.register_blueprint(analysis.bp)
    app.register_blueprint(report.bp)
    app.register_blueprint(health.bp)
    app.register_blueprint(web.bp)
    
    # 注册错误处理器
    register_error_handlers(app)
    
    # 注册请求钩子
    register_request_hooks(app)
    
    # 注册CLI命令
    # 初始化演示数据
    init_demo_data(app, load_demo_csv=not bool(os.environ.get('VERCEL')))
    
    return app

def init_demo_data(app, load_demo_csv=True):
    """初始化演示数据"""
    import os
    import csv
    from app.models import Sample, ExperimentRecord, MLModel, OptimizationReport, User
    
    with app.app_context():
        # 首先创建表(Vercel 内存数据库需要)
        db.create_all()

        # 添加演示用户
        if User.query.filter_by(username='admin').first() is None:
            user = User(username='admin')
            user.set_password('123456')
            db.session.add(user)
            db.session.commit()

        # 检查是否已有数据
        if load_demo_csv and Sample.query.first() is None:
            demo_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sample_data_large.csv')
            if os.path.exists(demo_file):
                try:
                    with open(demo_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for idx, row in enumerate(reader):
                            sample = Sample(
                                sample_id=f"DEMO_{idx+1:03d}",
                                experiment_round=1,
                                experiment_group='A'
                            )
                            db.session.add(sample)
                            db.session.flush()
                            
                            record = ExperimentRecord(
                                sample_id=sample.id,
                                feature_data={
                                    'reaction_temperature': float(row['reaction_temperature']),
                                    'reaction_time_min': float(row['reaction_time_min']),
                                    'ph_value': float(row['ph_value']),
                                    'catalyst_loading': float(row['catalyst_loading']),
                                    'solvent_polarity': float(row['solvent_polarity']),
                                    'stirring_speed_rpm': float(row['stirring_speed_rpm']),
                                    'reactant_ratio': float(row['reactant_ratio']),
                                    'crystallization_time_min': float(row['crystallization_time_min']),
                                    'target': int(row['target'])
                                }
                            )
                            db.session.add(record)
                    
                    db.session.commit()
                    app.logger.info("演示数据加载完成")
                except Exception as e:
                    app.logger.error(f"演示数据加载失败: {e}")
                    db.session.rollback()

def register_error_handlers(app):
    """注册错误处理器"""
    from flask import jsonify, render_template, request
    from werkzeug.exceptions import HTTPException

    def _wants_json():
        path = request.path or ''
        if path.startswith('/api/'):
            return True
        accept = request.headers.get('Accept', '')
        if 'application/json' in accept.lower():
            return True
        return False

    def _render_error_page(code, title, description, message=None):
        return render_template(
            'error.html',
            code=code,
            title=title,
            description=description,
            message=message
        ), code
    
    @app.errorhandler(400)
    def bad_request(error):
        if _wants_json():
            return jsonify({'error': '请求参数错误', 'message': str(error)}), 400
        return _render_error_page(400, '请求参数错误', '请求参数不符合预期，请检查输入后重试。', str(error))
    
    @app.errorhandler(401)
    def unauthorized(error):
        if _wants_json():
            return jsonify({'error': '未授权，请先登录'}), 401
        return _render_error_page(401, '未授权', '当前页面需要登录后访问，请重新登录。')
    
    @app.errorhandler(403)
    def forbidden(error):
        if _wants_json():
            return jsonify({'error': '权限不足'}), 403
        return _render_error_page(403, '权限不足', '你没有权限访问该资源。')
    
    @app.errorhandler(404)
    def not_found(error):
        if _wants_json():
            return jsonify({'error': '资源未找到'}), 404
        return _render_error_page(404, '资源未找到', '你访问的页面不存在，可能已被移动或删除。')
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        if _wants_json():
            return jsonify({'error': '方法不允许'}), 405
        return _render_error_page(405, '方法不允许', '请求方法不被允许，请返回并重新操作。', str(error))
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        if _wants_json():
            return jsonify({'error': '上传文件过大'}), 413
        return _render_error_page(413, '上传文件过大', '上传文件超过限制，请压缩或更换文件后重试。')
    
    @app.errorhandler(429)
    def too_many_requests(error):
        if _wants_json():
            return jsonify({'error': '请求过于频繁'}), 429
        return _render_error_page(429, '请求过于频繁', '请求过于频繁，请稍后再试。')
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f"服务器内部错误: {str(error)}")
        if _wants_json():
            return jsonify({'error': '服务器内部错误'}), 500
        return _render_error_page(500, '服务器内部错误', '系统运行异常，请稍后重试。')
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        # 处理非HTTP异常
        if isinstance(error, HTTPException):
            return error
        
        db.session.rollback()
        app.logger.error(f"未处理的异常: {str(error)}", exc_info=True)
        if _wants_json():
            return jsonify({'error': '服务器内部错误', 'message': str(error)}), 500
        return _render_error_page(500, '服务器内部错误', '系统运行异常，请稍后重试。', str(error))

def register_request_hooks(app):
    """注册请求钩子"""
    from flask import request
    import time
    
    @app.before_request
    def before_request():
        request.start_time = time.time()
    
    @app.after_request
    def after_request(response):
        if hasattr(request, 'start_time'):
            elapsed = time.time() - request.start_time
            app.logger.info(f"{request.method} {request.path} - {response.status_code} - {elapsed:.3f}s")
        return response

