from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required
from app import db
from app.models import Sample, ExperimentRecord
from app.services.data_service import DataService
from app.utils.decorators import handle_errors
from app.utils.validators import SampleCreateSchema, ExperimentRecordSchema
from pydantic import ValidationError
import os
from werkzeug.utils import secure_filename

bp = Blueprint('data', __name__, url_prefix='/api/data')
data_service = DataService()

@bp.route('/upload', methods=['POST'])
@login_required
@handle_errors
def upload_data():
    """上传实验数据文件"""
    if 'file' not in request.files:
        return jsonify({'error': '未找到文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '文件名为空'}), 400
    
    # 安全的文件名
    filename = secure_filename(file.filename)
    
    # 检查文件扩展名
    if '.' not in filename:
        return jsonify({'error': '文件必须有扩展名'}), 400
    
    file_ext = filename.rsplit('.', 1)[1].lower()
    if file_ext not in ['csv', 'xlsx', 'xls']:
        return jsonify({'error': '不支持的文件格式，仅支持CSV和Excel文件'}), 400
    
    # 确保上传目录存在（Vercel 跳过）
    upload_folder = current_app.config['UPLOAD_FOLDER']
    if not os.environ.get('VERCEL'):
        os.makedirs(upload_folder, exist_ok=True)
    
    # 保存文件
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)
    
    current_app.logger.info(f"文件上传成功: {filename}")
    
    try:
        file_type = 'csv' if file_ext == 'csv' else 'excel'
        df = data_service.load_data(filepath, file_type)
        
        return jsonify({
            'message': '文件上传成功',
            'filename': filename,
            'filepath': filepath,
            'rows': len(df),
            'columns': list(df.columns),
            'data_types': {col: str(dtype) for col, dtype in df.dtypes.items()}
        }), 200
    except Exception as e:
        current_app.logger.error(f"文件处理失败: {str(e)}")
        # 删除上传失败的文件
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': f'文件处理失败: {str(e)}'}), 500

@bp.route('/samples', methods=['GET'])
@login_required
def get_samples():
    """获取样本列表"""
    samples = Sample.query.all()
    return jsonify([{
        'id': s.id,
        'sample_id': s.sample_id,
        'experiment_round': s.experiment_round,
        'experiment_group': s.experiment_group,
        'created_at': s.created_at.isoformat()
    } for s in samples]), 200

@bp.route('/samples', methods=['POST'])
@login_required
@handle_errors
def create_sample():
    """创建样本记录"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请求体不能为空'}), 400
    
    # 数据验证
    try:
        validated_data = SampleCreateSchema(**data)
    except ValidationError as e:
        return jsonify({'error': '数据验证失败', 'details': e.errors()}), 400
    
    # 检查样本ID是否已存在
    if Sample.query.filter_by(sample_id=validated_data.sample_id).first():
        return jsonify({'error': '样本ID已存在'}), 400
    
    # 创建样本
    sample = Sample(
        sample_id=validated_data.sample_id,
        experiment_round=validated_data.experiment_round,
        experiment_group=validated_data.experiment_group
    )
    
    db.session.add(sample)
    db.session.commit()
    
    current_app.logger.info(f"样本创建成功: {sample.sample_id}")
    
    return jsonify({
        'message': '样本创建成功',
        'sample_id': sample.id,
        'sample_code': sample.sample_id
    }), 201

@bp.route('/samples/<int:sample_id>/records', methods=['POST'])
@login_required
@handle_errors
def add_experiment_record(sample_id):
    """添加实验记录"""
    # 检查样本是否存在
    sample = Sample.query.get(sample_id)
    if not sample:
        return jsonify({'error': '样本不存在'}), 404
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请求体不能为空'}), 400
    
    # 数据验证
    try:
        validated_data = ExperimentRecordSchema(**data)
    except ValidationError as e:
        return jsonify({'error': '数据验证失败', 'details': e.errors()}), 400
    
    # 化学数据校验
    is_valid, errors = data_service.validate_chemistry_data(validated_data.features)
    if not is_valid:
        return jsonify({'error': '化学数据校验失败', 'details': errors}), 400
    
    # 创建实验记录
    record = ExperimentRecord(
        sample_id=sample_id,
        feature_data=validated_data.features
    )
    
    db.session.add(record)
    db.session.commit()
    
    current_app.logger.info(f"实验记录添加成功: 样本ID={sample_id}, 记录ID={record.id}")
    
    return jsonify({
        'message': '实验记录添加成功',
        'record_id': record.id,
        'sample_id': sample_id
    }), 201

@bp.route('/samples/<int:sample_id>', methods=['GET'])
@login_required
@handle_errors
def get_sample(sample_id):
    """获取样本详情"""
    sample = Sample.query.get(sample_id)
    if not sample:
        return jsonify({'error': '样本不存在'}), 404
    
    # 获取样本的实验记录
    records = ExperimentRecord.query.filter_by(sample_id=sample_id).all()
    
    return jsonify({
        'id': sample.id,
        'sample_id': sample.sample_id,
        'experiment_round': sample.experiment_round,
        'experiment_group': sample.experiment_group,
        'created_at': sample.created_at.isoformat(),
        'records_count': len(records),
        'records': [{
            'id': r.id,
            'feature_data': r.feature_data,
            'created_at': r.created_at.isoformat()
        } for r in records]
    }), 200

@bp.route('/samples/<int:sample_id>', methods=['DELETE'])
@login_required
@handle_errors
def delete_sample(sample_id):
    """删除样本"""
    sample = Sample.query.get(sample_id)
    if not sample:
        return jsonify({'error': '样本不存在'}), 404
    
    # 删除相关的实验记录
    ExperimentRecord.query.filter_by(sample_id=sample_id).delete()
    
    db.session.delete(sample)
    db.session.commit()
    
    current_app.logger.info(f"样本删除成功: {sample.sample_id}")
    
    return jsonify({'message': '样本删除成功'}), 200

