import os

import pandas as pd
from flask import Blueprint, jsonify, request
from flask_login import login_required
from sklearn.model_selection import train_test_split

from app import db
from app.models import MLModel
from app.services.data_service import DataService
from app.services.model_service import ModelService

bp = Blueprint('model', __name__, url_prefix='/api/model')
model_service = ModelService()
data_service = DataService()


@bp.route('/train', methods=['POST'])
@login_required
def train_model():
    """训练模型"""
    data = request.get_json()
    df = pd.read_csv(data['data_path'])
    df_clean = data_service.clean_data(df)

    X = df_clean.drop(columns=[data['target_column']])
    y = df_clean[data['target_column']]

    categorical_cols = X.select_dtypes(include=['object']).columns.tolist()
    X_encoded = data_service.encode_features(X, categorical_cols)
    X_normalized = data_service.normalize_features(X_encoded)

    X_train, X_test, y_train, y_test = train_test_split(
        X_normalized, y, test_size=0.2, random_state=42
    )

    model_type = data.get('model_type', 'xgboost')
    if model_type == 'xgboost':
        model_service.train_xgboost(X_train, y_train, data.get('params'))
    elif model_type == 'random_forest':
        model_service.train_random_forest(X_train, y_train, data.get('params'))
    elif model_type == 'lightgbm':
        model_service.train_lightgbm(X_train, y_train, data.get('params'))
    else:
        return jsonify({'error': '不支持的模型类型'}), 400

    metrics = model_service.evaluate_model(X_test, y_test)
    model_filename = f"{model_type}_{data['name']}.pkl"
    filepath = model_service.save_model(model_filename)

    ml_model = MLModel(
        name=data['name'],
        version=data.get('version', '1.0'),
        model_type=model_type,
        file_path=filepath,
        metrics=metrics
    )

    db.session.add(ml_model)
    db.session.commit()

    return jsonify({
        'message': '模型训练成功',
        'model_id': ml_model.id,
        'metrics': metrics
    }), 201


@bp.route('/<int:model_id>', methods=['GET'])
@login_required
def get_model_detail(model_id):
    """获取单个模型详情"""
    model = MLModel.query.get_or_404(model_id)
    metrics = model.metrics or {}
    return jsonify({
        'id': model.id,
        'name': model.name,
        'version': model.version,
        'model_type': model.model_type,
        'status': 'active' if model.is_active else 'inactive',
        'is_active': model.is_active,
        'accuracy': metrics.get('accuracy', metrics.get('auc', 0)),
        'metrics': metrics,
        'created_at': model.created_at.isoformat()
    }), 200


@bp.route('/models', methods=['GET'])
@login_required
def get_models():
    """获取模型列表"""
    models = MLModel.query.all()
    return jsonify([{
        'id': m.id,
        'name': m.name,
        'version': m.version,
        'model_type': m.model_type,
        'metrics': m.metrics,
        'is_active': m.is_active,
        'created_at': m.created_at.isoformat()
    } for m in models]), 200


@bp.route('/models/<int:model_id>/activate', methods=['POST'])
@login_required
def activate_model(model_id):
    """激活模型"""
    MLModel.query.update({'is_active': False})
    model = MLModel.query.get_or_404(model_id)
    model.is_active = True
    db.session.commit()
    return jsonify({'message': '模型激活成功'}), 200


@bp.route('/predict', methods=['POST'])
@login_required
def predict():
    """预测"""
    data = request.get_json()

    active_model = MLModel.query.filter_by(is_active=True).first()
    if not active_model:
        return jsonify({'error': '没有激活的模型'}), 400

    model_service.load_model(os.path.basename(active_model.file_path))
    X = pd.DataFrame([data['features']])
    prediction = model_service.predict(X)

    return jsonify({
        'success_probability': float(prediction[0]),
        'model_id': active_model.id
    }), 200

