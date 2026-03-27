from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import MLModel, Sample, OptimizationReport
from app.services.model_service import ModelService
from app.services.attribution_service import AttributionService
import pandas as pd
import numpy as np
import os

bp = Blueprint('analysis', __name__, url_prefix='/api/analysis')

@bp.route('/shap', methods=['POST'])
@login_required
def calculate_shap():
    """计算SHAP值"""
    data = request.get_json()
    
    # 获取模型
    model_id = data.get('model_id')
    if model_id:
        model_record = MLModel.query.get_or_404(model_id)
    else:
        model_record = MLModel.query.filter_by(is_active=True).first()
        if not model_record:
            return jsonify({'error': '没有激活的模型'}), 400
    
    # 加载模型
    model_service = ModelService()
    model = model_service.load_model(os.path.basename(model_record.file_path))
    
    # 创建归因服务
    attribution_service = AttributionService(model)
    attribution_service.create_explainer()
    
    # 准备数据
    X = pd.DataFrame([data['features']])
    feature_names = list(data['features'].keys())
    
    # 计算个体解释
    local_explanation = attribution_service.get_local_explanation(X, feature_names)
    
    # 生成可视化
    waterfall_plot = attribution_service.generate_waterfall_plot(X, feature_names)
    force_plot = attribution_service.generate_force_plot(X, feature_names)
    
    # 获取Top 3特征
    top_features = local_explanation[:3]
    
    # 预测成功概率
    success_prob = float(model_service.predict(X)[0])
    
    # 保存优化报告
    if 'sample_id' in data:
        report = OptimizationReport(
            sample_id=data['sample_id'],
            model_id=model_record.id,
            success_probability=success_prob,
            shap_values={k: v for k, v in local_explanation},
            top_features=[{'feature': k, 'contribution': v} for k, v in top_features]
        )
        db.session.add(report)
        db.session.commit()
    
    return jsonify({
        'success_probability': success_prob,
        'shap_values': {k: v for k, v in local_explanation},
        'top_features': [{'feature': k, 'contribution': v} for k, v in top_features],
        'visualizations': {
            'waterfall_plot': waterfall_plot,
            'force_plot': force_plot
        }
    }), 200

@bp.route('/global-importance', methods=['POST'])
@login_required
def global_importance():
    """全局特征重要性分析"""
    data = request.get_json()
    
    # 获取模型
    model_record = MLModel.query.filter_by(is_active=True).first()
    if not model_record:
        return jsonify({'error': '没有激活的模型'}), 400
    
    # 加载模型
    model_service = ModelService()
    model = model_service.load_model(os.path.basename(model_record.file_path))
    
    # 创建归因服务
    attribution_service = AttributionService(model)
    attribution_service.create_explainer()
    
    # 加载数据集
    df = pd.read_csv(data['data_path'])
    X = df.drop(columns=[data['target_column']])
    feature_names = X.columns.tolist()
    
    # 计算全局重要性
    importance = attribution_service.get_global_importance(X, feature_names)
    
    # 生成摘要图
    summary_plot = attribution_service.generate_summary_plot(X, feature_names)
    
    return jsonify({
        'feature_importance': [{'feature': k, 'importance': v} for k, v in importance],
        'summary_plot': summary_plot
    }), 200

@bp.route('/reports/<int:sample_id>', methods=['GET'])
@login_required
def get_sample_reports(sample_id):
    """获取样本的分析报告"""
    reports = OptimizationReport.query.filter_by(sample_id=sample_id).all()
    
    return jsonify([{
        'id': r.id,
        'success_probability': r.success_probability,
        'top_features': r.top_features,
        'expert_advice': r.expert_advice,
        'created_at': r.created_at.isoformat()
    } for r in reports]), 200

@bp.route('/reports/<int:report_id>/advice', methods=['PUT'])
@login_required
def update_report_advice(report_id):
    """更新报告专家建议"""
    data = request.get_json()
    
    report = OptimizationReport.query.get_or_404(report_id)
    report.expert_advice = data['advice']
    
    db.session.commit()
    
    return jsonify({'message': '建议更新成功'}), 200

