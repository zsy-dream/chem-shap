import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_logger(app):
    """配置系统日志系统"""
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # 文件处理器
    file_handler = RotatingFileHandler(
        'logs/shap_experiment_system.log',
        maxBytes=10240000,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    ))
    file_handler.setLevel(logging.INFO)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    console_handler.setLevel(logging.DEBUG)
    
    # 清除旧的处理器防止重复
    app.logger.handlers.clear()
    
    # 配置应用日志
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.INFO)
    
    app.logger.info('智析实验 SHAP 系统启动完成 (SHAP Experiment System Startup)')

def log_api_call(func_name, user_id, params, result):
    """记录 API 接口调用"""
    logging.info(f"API Call: {func_name} | User: {user_id} | Params: {params} | Result: {result}")

def log_model_operation(model_name, action, details):
    """记录模型相关操作（加载、激活、删除等）"""
    logging.info(f"Model {action}: {model_name} | Details: {details}")

def log_shap_analysis(sample_id, success_prob, top_features):
    """记录 SHAP 归因分析执行日志"""
    logging.info(f"SHAP Analysis: Sample {sample_id} | Success Prob: {success_prob} | Top Features: {top_features}")

