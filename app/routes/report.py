from flask import Blueprint, jsonify, render_template, request, send_file
from flask_login import login_required

from app.models import OptimizationReport, MLModel, Sample

bp = Blueprint('report', __name__, url_prefix='/api/report')


def _level_meta(probability):
    if probability >= 0.75:
        return '优秀', '实验条件匹配度高，预计能够获得较好的产率或纯度表现。'
    if probability >= 0.5:
        return '良好', '实验条件总体可行，但仍有几个关键条件值得进一步优化。'
    return '待优化', '当前条件下实验结果稳定性一般，建议优先调整高影响因子。'


def _tips_from_features(top_features):
    tips = []
    for feature in (top_features or [])[:3]:
        feature_name = feature.get('display_name') or feature.get('feature')
        # In this chemical context, contribution > 0 means it adds to the success prob (good)
        # So it should be maintained. If < 0, it hinders success (bad).
        direction = '可以保持或适度增强该条件' if feature.get('contribution', 0) > 0 else '重点关注并尝试优化（重点调整）'
        tips.append(f'{feature_name} 对实验结果有显著影响，建议 {direction}。')
    return tips


@bp.route('/generate/<int:report_id>', methods=['GET'])
@bp.route('/<int:report_id>/generate', methods=['GET'])
@login_required
def generate_report(report_id):
    """生成化学实验分析报告预览 HTML"""
    report = OptimizationReport.query.get_or_404(report_id)
    sample = Sample.query.get(report.sample_id)
    model = MLModel.query.get(report.model_id)
    
    level_label, level_description = _level_meta(report.success_probability or 0)
    
    if report.expert_advice:
        optimization_tips = [tip.strip() for tip in report.expert_advice.split('\n') if tip.strip() and not tip.startswith('#')]
    else:
        optimization_tips = _tips_from_features(report.top_features)
    
    html_content = render_template(
        'report_preview.html',
        report=report,
        sample=sample,
        model=model,
        level_label=level_label,
        level_description=level_description,
        optimization_tips=optimization_tips
    )

    if request.args.get('response') == 'json':
        return jsonify({
            'html': html_content,
            'message': '报告生成成功'
        }), 200

    return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}


@bp.route('/export/<int:report_id>', methods=['GET'])
@bp.route('/<int:report_id>/export', methods=['GET'])
@login_required
def export_report(report_id):
    """导出报告为标准 JSON 格式"""
    report = OptimizationReport.query.get_or_404(report_id)
    sample = Sample.query.get(report.sample_id)
    level_label, level_description = _level_meta(report.success_probability or 0)

    export_data = {
        'sample': {
            'sample_id': sample.sample_id,
            'experiment_round': sample.experiment_round,
            'experiment_group': sample.experiment_group
        },
        'analysis': {
            'success_probability': report.success_probability,
            'result_level': level_label,
            'result_summary': level_description,
            'shap_values': report.shap_values,
            'top_features': report.top_features,
            'optimization_tips': _tips_from_features(report.top_features),
            'expert_advice': report.expert_advice,
            'created_at': report.created_at.isoformat()
        }
    }

    return jsonify(export_data), 200


@bp.route('/<int:report_id>/pdf', methods=['GET'])
@login_required
def export_report_pdf(report_id):
    """导出报告为 PDF（论文风格）"""
    report = OptimizationReport.query.get_or_404(report_id)
    sample = Sample.query.get(report.sample_id)
    model = MLModel.query.get(report.model_id)
    level_label, level_description = _level_meta(report.success_probability or 0)

    from app.services.pdf_service import PDFService
    from app.services.llm_service import LLMService

    pdf_service = PDFService()

    meta = {
        'school': '河南师范大学',
        'team': 'PIONEER工作室',
        'competition': '第十二届@际大学生创新大赛'
    }

    abstract_text = None
    conclusion_text = None
    keywords = None
    abstract_sections = None
    references = None
    try:
        llm = LLMService()
        top_features = report.top_features or []
        feature_lines = []
        for feat in top_features[:6]:
            name = feat.get('display_name') or feat.get('feature')
            contribution = feat.get('contribution', 0)
            value = feat.get('formatted_value') or feat.get('value')
            feature_lines.append(f"- {name}: 值={value}, 贡献={contribution:.4f}")

        prompt = f"""
请你以“科研论文写作”风格，为以下化学实验归因分析报告生成结构化内容。

【样本信息】
- 样本编号：{getattr(sample, 'sample_id', '-') if sample else '-'}
- 实验分组：{getattr(sample, 'experiment_group', '-') if sample else '-'}
- 实验轮次：{getattr(sample, 'experiment_round', '-') if sample else '-'}
- 预测成功率：{(report.success_probability or 0) * 100:.1f}%
- 结果等级：{level_label}

【关键影响因子（Top）】
{chr(10).join(feature_lines) if feature_lines else '- 无'}

【输出格式（必须严格遵守）】
关键词：词1；词2；词3（3-5个）
摘要-方法：...
摘要-结果：...
摘要-结论：...
结论：...（独立结论，80-140字）
参考文献：
[1] ...（GB/T 7714 格式）
[2] ...
[3] ...
"""
        response = llm.generate_response(prompt, system_message="你是一个专业的科研论文写作助手，擅长生成关键词、结构化摘要、结论与GB/T 7714参考文献。")
        if isinstance(response, str) and response.strip() and not response.strip().startswith('Error:'):
            from app.services.llm_paper_helper import parse_paper_response
            parsed = parse_paper_response(response)
            keywords = parsed.get('keywords') or None
            abstract_sections = parsed.get('abstract') or None
            references = parsed.get('references') or None
            conclusion_text = parsed.get('conclusion') or conclusion_text
    except Exception:
        abstract_text = None
        conclusion_text = None
        keywords = None
        abstract_sections = None
        references = None

    buffer = pdf_service.build_report_pdf(
        report=report,
        sample=sample,
        model=model,
        level_label=level_label,
        level_description=level_description,
        meta=meta,
        abstract_text=abstract_text,
        conclusion_text=conclusion_text,
        keywords=keywords,
        abstract_sections=abstract_sections,
        references=references
    )
    filename = f"experiment_report_{report_id}.pdf"
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

