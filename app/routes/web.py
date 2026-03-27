from collections import Counter
from functools import wraps
import os

import joblib
import numpy as np
import pandas as pd
from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from flask_login import login_user, logout_user

from app import db
from app.models import MLModel, ExperimentRecord, Sample, OptimizationReport, User
from app.services.llm_service import LLMService


bp = Blueprint('web', __name__)

FEATURE_LABELS = {
    'reaction_temperature': '反应温度',
    'reaction_time_min': '反应时间',
    'ph_value': 'pH值',
    'catalyst_loading': '催化剂添加量',
    'solvent_polarity': '溶剂极性',
    'stirring_speed_rpm': '搅拌转速',
    'reactant_ratio': '反应物配比',
    'crystallization_time_min': '结晶时间'
}


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return float(default)


def _bootstrap_ci_diff(control_values, opt_values, n_boot=1200, ci=0.95, seed=42):
    control = np.asarray(control_values, dtype=float)
    opt = np.asarray(opt_values, dtype=float)
    if control.size == 0 or opt.size == 0:
        return {
            'diff': 0.0,
            'ci_low': 0.0,
            'ci_high': 0.0,
            'n_control': int(control.size),
            'n_opt': int(opt.size)
        }

    rng = np.random.default_rng(seed)
    diffs = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        c = rng.choice(control, size=control.size, replace=True)
        o = rng.choice(opt, size=opt.size, replace=True)
        diffs[i] = o.mean() - c.mean()

    alpha = (1 - ci) / 2
    low = float(np.quantile(diffs, alpha))
    high = float(np.quantile(diffs, 1 - alpha))
    diff = float(opt.mean() - control.mean())
    return {
        'diff': round(diff, 2),
        'ci_low': round(low, 2),
        'ci_high': round(high, 2),
        'n_control': int(control.size),
        'n_opt': int(opt.size)
    }


def _permutation_pvalue_diff(control_values, opt_values, n_perm=3000, seed=42):
    control = np.asarray(control_values, dtype=float)
    opt = np.asarray(opt_values, dtype=float)
    if control.size == 0 or opt.size == 0:
        return 1.0

    rng = np.random.default_rng(seed)
    observed = float(opt.mean() - control.mean())
    combined = np.concatenate([control, opt])
    n_c = control.size
    count = 0
    for _ in range(n_perm):
        perm = rng.permutation(combined)
        c = perm[:n_c]
        o = perm[n_c:]
        diff = float(o.mean() - c.mean())
        if abs(diff) >= abs(observed):
            count += 1

    return float((count + 1) / (n_perm + 1))


def _build_group_compare(reports):
    groups_of_interest = {
        '对照组': '对照组',
        '优化组': '优化组'
    }
    grouped = {key: [] for key in groups_of_interest.keys()}

    for report in reports:
        sample = getattr(report, 'sample', None)
        group = getattr(sample, 'experiment_group', None) if sample else None
        if group in grouped:
            grouped[group].append(report)

    compare = {
        'groups': [],
        'avg_success_rate': [],
        'excellent_rate': [],
        'top_features': {},
        'significance': {}
    }

    for group_name in groups_of_interest.keys():
        items = grouped.get(group_name) or []
        compare['groups'].append(group_name)
        if not items:
            compare['avg_success_rate'].append(0)
            compare['excellent_rate'].append(0)
            compare['top_features'][group_name] = []
            continue

        probs = [(_safe_float(item.success_probability, 0) * 100) for item in items]
        avg_prob = sum(probs) / len(probs) if probs else 0
        excellent = len([p for p in probs if p >= 75])
        excellent_rate = (excellent / len(probs) * 100) if probs else 0
        compare['avg_success_rate'].append(round(avg_prob, 1))
        compare['excellent_rate'].append(round(excellent_rate, 1))

        feature_counter = Counter()
        for item in items:
            for rank, feature in enumerate((item.top_features or [])[:3], start=1):
                name = feature.get('display_name') or feature.get('feature')
                if name:
                    feature_counter[name] += max(1, 4 - rank)

        compare['top_features'][group_name] = [
            {'name': name, 'score': score}
            for name, score in feature_counter.most_common(3)
        ]

    control_items = grouped.get('对照组') or []
    opt_items = grouped.get('优化组') or []
    control_probs = [(_safe_float(item.success_probability, 0) * 100) for item in control_items]
    opt_probs = [(_safe_float(item.success_probability, 0) * 100) for item in opt_items]
    compare['significance']['avg_success_rate'] = _bootstrap_ci_diff(control_probs, opt_probs)
    compare['significance']['avg_success_rate']['p_value'] = round(
        _permutation_pvalue_diff(control_probs, opt_probs),
        4
    )

    control_exc = [1.0 if p >= 75 else 0.0 for p in control_probs]
    opt_exc = [1.0 if p >= 75 else 0.0 for p in opt_probs]
    rate_ci = _bootstrap_ci_diff(control_exc, opt_exc)
    rate_ci['diff'] = round(rate_ci['diff'] * 100, 2)
    rate_ci['ci_low'] = round(rate_ci['ci_low'] * 100, 2)
    rate_ci['ci_high'] = round(rate_ci['ci_high'] * 100, 2)
    rate_ci['p_value'] = round(_permutation_pvalue_diff(control_exc, opt_exc), 4)
    compare['significance']['excellent_rate'] = rate_ci

    return compare


def _build_improvement_story(reports):
    grouped = {}
    for report in reports:
        sample = getattr(report, 'sample', None)
        sid = getattr(sample, 'sample_id', None) if sample else None
        if not sid:
            continue
        grouped.setdefault(sid, []).append(report)

    best_sid = None
    best_len = 0
    for sid, items in grouped.items():
        if len(items) > best_len:
            best_len = len(items)
            best_sid = sid

    story = {
        'sample_id': best_sid or '-',
        'labels': [],
        'values': []
    }
    if not best_sid or best_len < 2:
        return story

    items = sorted(grouped[best_sid], key=lambda r: r.created_at)
    for idx, item in enumerate(items, start=1):
        story['labels'].append(f'第{idx}轮')
        story['values'].append(round((_safe_float(item.success_probability, 0) * 100), 2))
    return story

FEATURE_UNITS = {
    'reaction_temperature': '℃',
    'reaction_time_min': 'min',
    'ph_value': '',
    'catalyst_loading': '%',
    'solvent_polarity': '',
    'stirring_speed_rpm': 'rpm',
    'reactant_ratio': '',
    'crystallization_time_min': 'min'
}

GROUP_LABELS = {
    'A': '甲组',
    'B': '乙组',
    'M': 'A组',
    'F': 'B组',
    '男': '甲组',
    '女': '乙组'
}


def login_required_web(f):
    """Web页面登录装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('web.login'))
        return f(*args, **kwargs)

    return decorated_function


def get_feature_label(feature_name):
    return FEATURE_LABELS.get(feature_name, feature_name.replace('_', ' ').title())


def format_feature_value(feature_name, value):
    if value is None:
        return '-'
    unit = FEATURE_UNITS.get(feature_name, '')
    if isinstance(value, float):
        value_text = f'{value:.2f}'
    else:
        value_text = str(value)
    return f'{value_text}{unit}'


def get_group_label(group_code):
    return GROUP_LABELS.get(group_code, group_code or '未分组')


def get_result_level(probability):
    if probability >= 0.75:
        return {
            'key': 'excellent',
            'label': '优秀',
            'badge': 'success',
            'description': '当前实验条件匹配度较高，预计产率或纯度表现较好。'
        }
    if probability >= 0.5:
        return {
            'key': 'good',
            'label': '良好',
            'badge': 'primary',
            'description': '当前实验具备较好的成功潜力，但仍存在优化空间。'
        }
    return {
        'key': 'needs_optimization',
        'label': '待优化',
        'badge': 'warning',
        'description': '当前实验条件偏离最佳区间，建议先调整关键影响因素。'
    }


def build_optimization_tip(feature_name, contribution):
    label = get_feature_label(feature_name)
    if feature_name == 'reaction_temperature':
        return f'{label}对预测影响显著，建议围绕 75-90℃ 区间做梯度优化。'
    if feature_name == 'ph_value':
        return f'{label}贡献较高，建议优先验证弱酸到中性范围对实验结果的影响。'
    if feature_name == 'catalyst_loading':
        return f'{label}是关键变量，可采用小步长方式重新筛选最佳添加量。'
    if feature_name == 'reactant_ratio':
        return f'{label}影响明显，建议围绕 1.0 附近进行精细调参。'
    direction = '重点回看并优化' if contribution > 0 else '继续保持并微调'
    return f'{label}对模型判断影响较大，建议{direction}该实验条件。'


def build_feature_items(feature_data):
    feature_items = []
    for feature_name, value in (feature_data or {}).items():
        feature_items.append({
            'name': feature_name,
            'label': get_feature_label(feature_name),
            'value': value,
            'formatted_value': format_feature_value(feature_name, value)
        })
    return feature_items


def build_dashboard_data(records, reports):
    latest_records = list(reversed(records[:8])) if records else []
    experiment_labels = []
    temperature_series = []
    catalyst_series = []
    ph_series = []

    avg_features = {
        '反应温度': [],
        '反应时间': [],
        'pH值': [],
        '催化剂添加量': [],
        '搅拌转速': []
    }

    for index, record in enumerate(latest_records, start=1):
        data = record.feature_data or {}
        experiment_labels.append(f'样本{index}')
        temperature_series.append(round(float(data.get('reaction_temperature', 0)), 2))
        catalyst_series.append(round(float(data.get('catalyst_loading', 0)), 2))
        ph_series.append(round(float(data.get('ph_value', 0)), 2))
        avg_features['反应温度'].append(float(data.get('reaction_temperature', 0)) / 12)
        avg_features['反应时间'].append(float(data.get('reaction_time_min', 0)) / 24)
        avg_features['pH值'].append(float(data.get('ph_value', 0)) * 8)
        avg_features['催化剂添加量'].append(float(data.get('catalyst_loading', 0)) * 12)
        avg_features['搅拌转速'].append(float(data.get('stirring_speed_rpm', 0)) / 10)

    level_counter = Counter()
    for report in reports:
        level_counter[get_result_level(report.success_probability or 0)['label']] += 1

    probability_labels = []
    probability_values = []
    for report in list(reversed(reports[:12])):
        sample_name = report.sample.sample_id if getattr(report, 'sample', None) else f'报告{report.id}'
        probability_labels.append(sample_name)
        probability_values.append(round((report.success_probability or 0) * 100, 2))

    group_counter = Counter([getattr(item, 'experiment_group', None) for item in Sample.query.all()])
    group_counter.pop(None, None)

    group_compare = _build_group_compare(reports)
    improvement_story = _build_improvement_story(reports)

    correlation = {
        'labels': [],
        'matrix': []
    }
    try:
        feature_keys = [
            'reaction_temperature',
            'reaction_time_min',
            'ph_value',
            'catalyst_loading',
            'solvent_polarity',
            'stirring_speed_rpm',
            'reactant_ratio',
            'crystallization_time_min'
        ]
        rows = []
        for record in records[:240]:
            data = record.feature_data or {}
            if isinstance(data, dict):
                rows.append({key: data.get(key) for key in feature_keys})
        if rows:
            df = pd.DataFrame(rows)
            df = df.apply(pd.to_numeric, errors='coerce')
            corr_df = df.corr().fillna(0).round(2)
            correlation['labels'] = [get_feature_label(key) for key in feature_keys]
            correlation['matrix'] = corr_df.values.tolist()
    except Exception:
        correlation = {
            'labels': [],
            'matrix': []
        }

    return {
        'experiment_labels': experiment_labels,
        'temperature_series': temperature_series,
        'catalyst_series': catalyst_series,
        'ph_series': ph_series,
        'correlation': correlation,
        'probability_timeline': {
            'labels': probability_labels,
            'values': probability_values
        },
        'result_distribution': {
            'labels': ['优秀', '良好', '待优化'],
            'values': [
                level_counter.get('优秀', 0),
                level_counter.get('良好', 0),
                level_counter.get('待优化', 0)
            ]
        },
        'group_distribution': {
            'labels': list(group_counter.keys()),
            'values': list(group_counter.values())
        },
        'group_compare': group_compare,
        'improvement_story': improvement_story,
        'radar': {
            'labels': list(avg_features.keys()),
            'values': [
                round(sum(values) / len(values), 2) if values else 0
                for values in avg_features.values()
            ]
        }
    }


def build_showcase_context(records, reports, models):
    latest_report = reports[0] if reports else None
    featured_report = max(reports, key=lambda item: item.success_probability or 0) if reports else None
    latest_record = records[0] if records else None

    feature_counter = Counter()
    for report in reports[:12]:
        for rank, feature in enumerate((report.top_features or [])[:3], start=1):
            feature_counter[feature.get('display_name') or feature.get('feature')] += max(1, 4 - rank)

    hotspot_labels = []
    hotspot_values = []
    for name, score in feature_counter.most_common(5):
        hotspot_labels.append(name)
        hotspot_values.append(score)

    probability_labels = []
    probability_values = []
    for report in reversed(reports[:8]):
        sample_name = report.sample.sample_id if getattr(report, 'sample', None) else f'报告{report.id}'
        probability_labels.append(sample_name)
        probability_values.append(round((report.success_probability or 0) * 100, 2))

    model_labels = []
    model_scores = []
    for model in models:
        model_labels.append(model.name)
        model_scores.append(round((model.metrics or {}).get('accuracy', (model.metrics or {}).get('auc', 0)) * 100, 2))

    spotlight_features = []
    if latest_record:
        for name, value in list((latest_record.feature_data or {}).items())[:4]:
            spotlight_features.append({
                'label': get_feature_label(name),
                'value': format_feature_value(name, value)
            })

    rotating_reports = []
    for report in reports[:6]:
        level = get_result_level(report.success_probability or 0)
        rotating_reports.append({
            'report_id': report.id,
            'sample_id': report.sample.sample_id if getattr(report, 'sample', None) else f'报告{report.id}',
            'probability': round((report.success_probability or 0) * 100, 1),
            'level_label': level['label'],
            'level_badge': level['badge'],
            'summary': level['description'],
            'created_at': report.created_at.strftime('%m-%d %H:%M'),
            'top_features': [
                item.get('display_name') or get_feature_label(item.get('feature'))
                for item in (report.top_features or [])[:3]
            ]
        })

    return {
        'hotspot': {
            'labels': hotspot_labels,
            'values': hotspot_values
        },
        'probability_timeline': {
            'labels': probability_labels,
            'values': probability_values
        },
        'model_scores': {
            'labels': model_labels,
            'values': model_scores
        },
        'spotlight_features': spotlight_features,
        'rotating_reports': rotating_reports,
        'story_steps': [
            {'title': '实验条件录入', 'desc': '采集反应温度、pH、催化剂添加量等实验变量。'},
            {'title': '模型推断', 'desc': '调用已激活模型预测优质结果概率。'},
            {'title': 'SHAP归因', 'desc': '解释每个变量对最终预测的贡献方向与强度。'},
            {'title': '优化建议', 'desc': '生成适合课堂展示和答辩讲解的实验调参建议。'}
        ]
    }


def build_snapshot_context(report):
    sample = report.sample
    record = None
    if sample:
        record = ExperimentRecord.query.filter_by(sample_id=sample.id).order_by(
            ExperimentRecord.created_at.desc()
        ).first()
    record_features = []
    if record:
        for name, value in list((record.feature_data or {}).items())[:6]:
            record_features.append({
                'label': get_feature_label(name),
                'value': format_feature_value(name, value)
            })

    top_features = report.top_features or []
    positive_features = [item for item in top_features if item.get('contribution', 0) > 0][:2]
    warning_features = [item for item in top_features if item.get('contribution', 0) < 0][:2]

    return {
        'level': get_result_level(report.success_probability or 0),
        'record_features': record_features,
        'positive_features': positive_features,
        'warning_features': warning_features,
        'optimization_text': report.expert_advice or '建议围绕关键影响因子做梯度实验，寻找更优条件区间。'
    }


@bp.route('/')
def index():
    """首页"""
    if 'user_id' not in session:
        return redirect(url_for('web.login'))

    records = ExperimentRecord.query.order_by(ExperimentRecord.created_at.desc()).all()
    reports = OptimizationReport.query.order_by(OptimizationReport.created_at.desc()).all()
    models_list = MLModel.query.order_by(MLModel.created_at.desc()).all()

    avg_success_rate = 0
    if reports:
        avg_success_rate = round(sum([(item.success_probability or 0) for item in reports]) / len(reports) * 100, 1)

    cv_accuracy = None
    active_model = MLModel.query.filter_by(is_active=True).first()
    if active_model and isinstance(active_model.metrics, dict):
        raw_value = active_model.metrics.get('accuracy', active_model.metrics.get('auc'))
        if raw_value is not None:
            cv_accuracy = round(float(raw_value) * 100, 1)

    stats = {
        'samples': Sample.query.count(),
        'models': MLModel.query.count(),
        'analyses': OptimizationReport.query.count(),
        'active_models': MLModel.query.filter_by(is_active=True).count(),
        'avg_success_rate': avg_success_rate,
        'cv_accuracy': cv_accuracy
    }
    dashboard = build_dashboard_data(records, reports)
    showcase = build_showcase_context(records, reports, models_list)
    import json
    dashboard_json = json.dumps(dashboard)
    showcase_json = json.dumps(showcase)
    return render_template(
        'index.html',
        stats=stats,
        dashboard_json=dashboard_json,
        showcase_json=showcase_json,
        showcase=showcase,
        dashboard=dashboard
    )


@bp.route('/presentation')
@login_required_web
def presentation():
    """挑战杯答辩大屏页"""
    records = ExperimentRecord.query.order_by(ExperimentRecord.created_at.desc()).all()
    reports = OptimizationReport.query.order_by(OptimizationReport.created_at.desc()).all()
    models_list = MLModel.query.order_by(MLModel.created_at.desc()).all()
    stats = {
        'samples': Sample.query.count(),
        'models': MLModel.query.count(),
        'analyses': OptimizationReport.query.count(),
        'active_models': MLModel.query.filter_by(is_active=True).count()
    }
    dashboard = build_dashboard_data(records, reports)
    showcase = build_showcase_context(records, reports, models_list)
    autoplay_mode = request.args.get('mode') == 'autoplay'
    return render_template(
        'presentation.html',
        stats=stats,
        dashboard=dashboard,
        showcase=showcase,
        autoplay_mode=autoplay_mode,
        get_result_level=get_result_level
    )


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if 'user_id' in session:
        return redirect(url_for('web.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            session['user_id'] = user.id
            session['username'] = user.username
            flash('登录成功！', 'success')
            return redirect(url_for('web.index'))
        flash('用户名或密码错误', 'danger')

    return render_template('login.html')


@bp.route('/logout')
def logout():
    """退出登录"""
    logout_user()
    session.clear()
    flash('已退出登录', 'info')
    return redirect(url_for('web.login'))


@bp.route('/samples')
@login_required_web
def samples():
    """实验样本列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 10

    samples_pagination = Sample.query.order_by(Sample.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    latest_reports = {}
    for report in OptimizationReport.query.order_by(OptimizationReport.created_at.desc()).all():
        if report.sample_id not in latest_reports:
            latest_reports[report.sample_id] = report
    
    samples_list = Sample.query.all()
    # Calculate group distribution
    group_counts = Counter([s.experiment_group for s in samples_list])
    group_stats = {
        'labels': list(group_counts.keys()),
        'values': list(group_counts.values())
    }

    avg_prob = 0
    best_prob = 0
    best_sample_id = "-"
    scatter_data = []

    valid_reports_count = 0
    for s in samples_list:
        if s.id in latest_reports:
            r = latest_reports[s.id]
            prob = r.success_probability or 0
            avg_prob += prob
            valid_reports_count += 1
            if prob > best_prob:
                best_prob = prob
                best_sample_id = s.sample_id
            
            # Extract temp if available for scatter
            temp = 0
            # get latest record
            latest_rec = ExperimentRecord.query.filter_by(sample_id=s.id).order_by(ExperimentRecord.created_at.desc()).first()
            if latest_rec and isinstance(latest_rec.feature_data, dict):
                temp = latest_rec.feature_data.get('reaction_temperature', 0)
            
            scatter_data.append({'x': temp, 'y': prob * 100})

    if valid_reports_count > 0:
        avg_prob = (avg_prob / valid_reports_count) * 100
    else:
        avg_prob = 0
        
    best_prob = best_prob * 100

    import json
    group_stats_json = json.dumps(group_stats)
    scatter_data_json = json.dumps(scatter_data)
    
    return render_template(
        'samples.html',
        samples=samples_pagination,
        latest_reports=latest_reports,
        group_stats_json=group_stats_json,
        scatter_data_json=scatter_data_json,
        avg_prob=avg_prob,
        best_prob=best_prob,
        best_sample_id=best_sample_id,
        get_group_label=get_group_label
    )


@bp.route('/samples/<int:sample_id>')
@login_required_web
def sample_detail(sample_id):
    """实验样本详情"""
    sample = Sample.query.get_or_404(sample_id)
    records = ExperimentRecord.query.filter_by(sample_id=sample_id).order_by(
        ExperimentRecord.created_at.desc()
    ).all()
    latest_report = OptimizationReport.query.filter_by(sample_id=sample_id).order_by(
        OptimizationReport.created_at.desc()
    ).first()

    record_cards = []
    for record in records:
        feature_items = build_feature_items(record.feature_data)
        record_cards.append({
            'record': record,
            'feature_items': feature_items,
            'highlight_items': feature_items[:4]
        })

    all_reports = OptimizationReport.query.filter_by(sample_id=sample_id).order_by(
        OptimizationReport.created_at.asc()
    ).all()
    
    import json
    history_trend = {
        'labels': [r.created_at.strftime('%m-%d %H:%M') for r in all_reports],
        'values': [round(r.success_probability * 100, 1) for r in all_reports]
    }
    history_json = json.dumps(history_trend)

    return render_template(
        'sample_detail.html',
        sample=sample,
        records=records,
        record_cards=record_cards,
        latest_report=latest_report,
        history_json=history_json,
        get_group_label=get_group_label,
        get_result_level=get_result_level
    )


@bp.route('/analysis')
@login_required_web
def analysis():
    """SHAP分析页面"""
    samples = Sample.query.order_by(Sample.created_at.desc()).all()
    models = MLModel.query.filter_by(is_active=True).all()
    return render_template(
        'analysis.html',
        samples=samples,
        models=models,
        feature_labels=FEATURE_LABELS,
        get_group_label=get_group_label
    )


@bp.route('/models')
@login_required_web
def models():
    """模型管理页面"""
    models_list = MLModel.query.order_by(MLModel.created_at.desc()).all()
    scores = [m.metrics.get('accuracy', m.metrics.get('auc', 0)) for m in models_list if m.metrics]
    avg_accuracy = sum(scores) / len(scores) if scores else 0
    
    import json
    perf_data = {
        'labels': [m.name[:10] for m in models_list],
        'values': [round(m.metrics.get('accuracy', m.metrics.get('auc', 0)) * 100, 1) if m.metrics else 0 for m in models_list]
    }
    models_json = json.dumps(perf_data)
    
    return render_template('models.html', models=models_list, avg_accuracy=avg_accuracy, models_json=models_json)


@bp.route('/reports')
@login_required_web
def reports():
    """报告列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 10

    reports_pagination = OptimizationReport.query.order_by(
        OptimizationReport.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return render_template('reports.html', reports=reports_pagination, get_result_level=get_result_level)


@bp.route('/reports/<int:report_id>')
@login_required_web
def report_detail(report_id):
    """报告详情"""
    report = OptimizationReport.query.get_or_404(report_id)
    return render_template('report_detail.html', report=report, get_result_level=get_result_level)


@bp.route('/reports/<int:report_id>/snapshot')
@login_required_web
def report_snapshot(report_id):
    """答辩截图页"""
    report = OptimizationReport.query.get_or_404(report_id)
    snapshot = build_snapshot_context(report)
    return render_template(
        'report_snapshot.html',
        report=report,
        snapshot=snapshot,
        get_result_level=get_result_level
    )


@bp.route('/train_model', methods=['POST'])
@login_required_web
def train_model_web():
    """Web界面训练模型"""
    try:
        from sklearn.model_selection import train_test_split

        from app.services.data_service import DataService
        from app.services.model_service import ModelService

        model_service = ModelService()
        data_service = DataService()

        name = request.form.get('name')
        model_type = request.form.get('model_type', 'xgboost')
        target_column = request.form.get('target_column', 'target')
        test_ratio = float(request.form.get('test_ratio', 0.2))

        if 'data_file' not in request.files:
            flash('请上传数据文件', 'danger')
            return redirect(url_for('web.models'))

        file = request.files['data_file']
        if file.filename == '':
            flash('请选择文件', 'danger')
            return redirect(url_for('web.models'))

        upload_folder = 'uploads'
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, file.filename)
        file.save(filepath)

        df = pd.read_csv(filepath)
        if target_column not in df.columns:
            flash(f'数据中不存在目标列: {target_column}', 'danger')
            return redirect(url_for('web.models'))

        df_clean = data_service.clean_data(df)
        X = df_clean.drop(columns=[target_column])
        y = df_clean[target_column]

        categorical_cols = X.select_dtypes(include=['object']).columns.tolist()
        X_encoded = data_service.encode_features(X, categorical_cols)
        X_normalized = data_service.normalize_features(X_encoded)

        X_train, X_test, y_train, y_test = train_test_split(
            X_normalized, y, test_size=test_ratio, random_state=42
        )

        if model_type == 'xgboost':
            model_service.train_xgboost(X_train, y_train)
        elif model_type == 'random_forest':
            model_service.train_random_forest(X_train, y_train)
        elif model_type == 'lightgbm':
            model_service.train_lightgbm(X_train, y_train)
        else:
            flash('不支持的模型类型', 'danger')
            return redirect(url_for('web.models'))

        metrics = model_service.evaluate_model(X_test, y_test)
        model_filename = f"{model_type}_{name}.pkl"
        model_filepath = model_service.save_model(model_filename)

        ml_model = MLModel(
            name=name,
            version='1.0',
            model_type=model_type,
            file_path=model_filepath,
            metrics=metrics,
            is_active=False
        )

        db.session.add(ml_model)
        db.session.commit()

        display_score = metrics.get("accuracy", metrics.get("auc", 0))
        flash(f'模型训练成功！当前综合得分: {display_score * 100:.2f}%', 'success')
        return redirect(url_for('web.models'))

    except Exception as error:
        flash(f'训练失败: {str(error)}', 'danger')
        return redirect(url_for('web.models'))


@bp.route('/upload_record/<int:sample_id>', methods=['POST'])
@login_required_web
def upload_record_web(sample_id):
    """Web界面上传实验记录"""
    try:
        if 'data_file' not in request.files:
            flash('请上传数据文件', 'danger')
            return redirect(url_for('web.sample_detail', sample_id=sample_id))

        file = request.files['data_file']
        if file.filename == '':
            flash('请选择文件', 'danger')
            return redirect(url_for('web.sample_detail', sample_id=sample_id))

        upload_folder = 'uploads'
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, file.filename)
        file.save(filepath)

        df = pd.read_csv(filepath)
        if len(df) > 0:
            feature_data = df.iloc[0].to_dict()
            record = ExperimentRecord(
                sample_id=sample_id,
                feature_data=feature_data
            )
            db.session.add(record)
            db.session.commit()
            flash('实验记录上传成功！', 'success')
        else:
            flash('数据文件为空', 'warning')

        return redirect(url_for('web.sample_detail', sample_id=sample_id))

    except Exception as error:
        flash(f'上传失败: {str(error)}', 'danger')
        return redirect(url_for('web.sample_detail', sample_id=sample_id))


@bp.route('/activate_model/<int:model_id>', methods=['POST'])
@login_required_web
def activate_model_web(model_id):
    """激活模型"""
    try:
        MLModel.query.update({'is_active': False})
        model = MLModel.query.get_or_404(model_id)
        model.is_active = True
        db.session.commit()
        flash('模型激活成功！', 'success')
    except Exception as error:
        flash(f'激活失败: {str(error)}', 'danger')

    return redirect(url_for('web.models'))


@bp.route('/perform_analysis', methods=['POST'])
@login_required_web
def perform_analysis():
    """执行SHAP分析"""
    try:
        from app.services.attribution_service import AttributionService

        sample_id = request.form.get('sample_id', type=int)
        model_id = request.form.get('model_id', type=int)
        top_n = request.form.get('top_n', 8, type=int)

        if not sample_id or not model_id:
            return jsonify({'error': '请选择实验样本和模型'}), 400

        sample = Sample.query.get_or_404(sample_id)
        ml_model = MLModel.query.get_or_404(model_id)
        record = ExperimentRecord.query.filter_by(sample_id=sample_id).order_by(
            ExperimentRecord.created_at.desc()
        ).first()

        if not record:
            return jsonify({'error': '该样本没有实验记录，请先上传实验数据'}), 400

        model_path = ml_model.file_path
        if not os.path.exists(model_path):
            return jsonify({'error': f'模型文件不存在: {model_path}'}), 400

        model = joblib.load(model_path)
        feature_data = record.feature_data or {}
        X = pd.DataFrame([feature_data])
        feature_names = X.columns.tolist()

        if hasattr(model, 'predict_proba'):
            success_probability = float(model.predict_proba(X.values)[0][1])
        else:
            prediction = model.predict(X.values)
            success_probability = float(prediction[0])

        attribution_service = AttributionService(model)
        attribution_service.create_explainer()
        shap_values = attribution_service.calculate_shap_values(X)
        local_explanation = attribution_service.get_local_explanation(X, feature_names)

        top_features = []
        for feature, contribution in local_explanation[:top_n]:
            raw_value = feature_data.get(feature, 0)
            top_features.append({
                'feature': feature,
                'display_name': get_feature_label(feature),
                'value': float(raw_value),
                'formatted_value': format_feature_value(feature, raw_value),
                'contribution': float(contribution),
                'impact': 'positive' if contribution > 0 else 'negative'
            })

        # 生成 AI 专家建议 (华为云 ModelArts MaaS DeepSeek-V3.2)
        llm_service = LLMService()
        sample_meta = {
            'sample_id': sample.sample_id,
            'experiment_round': sample.experiment_round,
            'experiment_group': sample.experiment_group
        }
        ai_advice = llm_service.generate_optimization_advice(sample_meta, success_probability, top_features)
        
        # 将建议按行分割为列表，方便前端展示
        optimization_tips = [tip.strip() for tip in ai_advice.split('\n') if tip.strip() and not tip.startswith('#')]

        result_level = get_result_level(success_probability)

        report = OptimizationReport(
            sample_id=sample.id,
            model_id=ml_model.id,
            success_probability=success_probability,
            shap_values={'values': shap_values.tolist() if hasattr(shap_values, 'tolist') else shap_values},
            top_features=top_features,
            expert_advice=ai_advice
        )

        db.session.add(report)
        db.session.commit()

        return jsonify({
            'success': True,
            'report_id': report.id,
            'success_probability': success_probability,
            'result_level': result_level['key'],
            'result_label': result_level['label'],
            'result_description': result_level['description'],
            'top_features': top_features,
            'optimization_tips': optimization_tips,
            'message': '分析完成！'
        }), 200

    except Exception as error:
        import traceback

        error_trace = traceback.format_exc()
        print(f"分析错误: {error_trace}")
        return jsonify({'error': f'分析失败: {str(error)}'}), 500


@bp.route('/case-study')
@login_required_web
def case_study():
    """案例对比页：展示一个代表性样本的完整优化故事线"""
    # 找出拥有最多报告的样本作为案例
    reports = OptimizationReport.query.order_by(OptimizationReport.created_at.asc()).all()
    grouped = {}
    for report in reports:
        sample = getattr(report, 'sample', None)
        sid = getattr(sample, 'sample_id', None) if sample else None
        if sid:
            grouped.setdefault(sid, []).append(report)

    # 选择报告最多的样本作为案例
    case_sid = None
    case_reports = []
    for sid, items in grouped.items():
        if len(items) > len(case_reports):
            case_reports = items
            case_sid = sid

    if not case_reports:
        # 如果没有报告，重定向到首页
        flash('暂无足够案例数据，请先进行分析', 'warning')
        return redirect(url_for('web.index'))

    case_sample = case_reports[0].sample

    # 构建轮次时间线数据
    round_timeline = []
    for idx, report in enumerate(case_reports, start=1):
        top3 = (report.top_features or [])[:3]
        round_data = {
            'round': idx,
            'round_label': f'第{idx}轮',
            'probability': round((report.success_probability or 0) * 100, 1),
            'created_at': report.created_at.strftime('%m-%d %H:%M'),
            'top3_features': [
                {
                    'name': item.get('display_name') or item.get('feature', '未知'),
                    'value': item.get('formatted_value') or str(item.get('value', '-')),
                    'contribution': round(item.get('contribution', 0), 3),
                    'impact': 'positive' if item.get('contribution', 0) > 0 else 'negative'
                }
                for item in top3
            ],
            'advice': (report.expert_advice or '无建议').strip()
        }
        round_timeline.append(round_data)

    # 构建前后对比数据（第一轮 vs 最后一轮）
    first_round = round_timeline[0]
    last_round = round_timeline[-1]
    improvement = last_round['probability'] - first_round['probability']

    before_after = {
        'first_probability': first_round['probability'],
        'last_probability': last_round['probability'],
        'improvement': round(improvement, 1),
        'improvement_pct': round(improvement / max(first_round['probability'], 1) * 100, 1),
        'first_top3': first_round['top3_features'],
        'last_top3': last_round['top3_features']
    }

    # 关键因子变化追踪（找出变化最大的因子）
    feature_evolution = {}
    for round_data in round_timeline:
        for feat in round_data['top3_features']:
            name = feat['name']
            if name not in feature_evolution:
                feature_evolution[name] = {
                    'name': name,
                    'first_contribution': feat['contribution'],
                    'last_contribution': feat['contribution'],
                    'trend': [feat['contribution']]
                }
            else:
                feature_evolution[name]['last_contribution'] = feat['contribution']
                feature_evolution[name]['trend'].append(feat['contribution'])

    # 计算每个因子的变化幅度
    for name, data in feature_evolution.items():
        data['change'] = round(data['last_contribution'] - data['first_contribution'], 3)
        data['abs_change'] = abs(data['change'])

    # 按变化幅度排序，取前3
    top_changed_features = sorted(
        feature_evolution.values(),
        key=lambda x: x['abs_change'],
        reverse=True
    )[:3]

    import json
    timeline_json = json.dumps({
        'labels': [r['round_label'] for r in round_timeline],
        'values': [r['probability'] for r in round_timeline]
    })

    return render_template(
        'case_study.html',
        sample=case_sample,
        round_timeline=round_timeline,
        before_after=before_after,
        top_changed_features=top_changed_features,
        timeline_json=timeline_json,
        round_count=len(round_timeline),
        get_group_label=get_group_label
    )


@bp.route('/sensitivity')
@login_required_web
def sensitivity_analysis():
    """因子敏感性分析页"""
    from app.services.sensitivity_service import SensitivityService
    import numpy as np

    def _json_safe(value):
        if isinstance(value, dict):
            return {k: _json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [_json_safe(v) for v in value]
        if isinstance(value, np.ndarray):
            return [_json_safe(v) for v in value.tolist()]
        if isinstance(value, np.generic):
            return value.item()
        return value
    
    # 获取激活的模型
    active_model = MLModel.query.filter_by(is_active=True).first()
    if not active_model:
        flash('请先激活一个模型进行敏感性分析', 'warning')
        return redirect(url_for('web.models'))
    
    # 加载模型
    if not os.path.exists(active_model.file_path):
        flash('模型文件不存在', 'danger')
        return redirect(url_for('web.models'))
    
    model = joblib.load(active_model.file_path)
    service = SensitivityService(model)
    
    # 获取基准样本（最新的实验记录）
    latest_record = ExperimentRecord.query.order_by(ExperimentRecord.created_at.desc()).first()
    base_features = latest_record.feature_data if latest_record else {}
    
    # 获取所有可用特征
    feature_options = [
        {'key': k, 'label': v['label'], 'unit': v['unit']}
        for k, v in SensitivityService.FEATURE_CONFIG.items()
    ]
    
    # 获取URL参数
    feature_x = request.args.get('feature_x', 'reaction_temperature')
    feature_y = request.args.get('feature_y', 'ph_value')
    
    # 执行双因素热力图分析
    heatmap_data = None
    single_sensitivities = []
    
    try:
        heatmap_data = service.two_feature_heatmap(base_features, feature_x, feature_y, num_points=15)
        
        # 同时生成所有特征的单因素敏感性排名
        single_sensitivities = service.all_features_sensitivity(base_features)
    except Exception as e:
        flash(f'敏感性分析出错: {str(e)}', 'danger')
    
    import json
    heatmap_json = json.dumps(_json_safe(heatmap_data)) if heatmap_data else '{}'
    sensitivity_json = json.dumps(_json_safe(single_sensitivities))
    
    return render_template(
        'sensitivity.html',
        feature_options=feature_options,
        feature_x=feature_x,
        feature_y=feature_y,
        base_sample=latest_record.sample if latest_record else None,
        heatmap_json=heatmap_json,
        sensitivity_json=sensitivity_json,
        model_name=active_model.name
    )


@bp.route('/api/sensitivity/analyze', methods=['POST'])
@login_required_web
def api_sensitivity_analyze():
    """AJAX API：执行敏感性分析"""
    from app.services.sensitivity_service import SensitivityService
    import numpy as np

    def _json_safe(value):
        if isinstance(value, dict):
            return {k: _json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [_json_safe(v) for v in value]
        if isinstance(value, np.ndarray):
            return [_json_safe(v) for v in value.tolist()]
        if isinstance(value, np.generic):
            return value.item()
        return value
    
    try:
        data = request.get_json()
        feature_x = data.get('feature_x', 'reaction_temperature')
        feature_y = data.get('feature_y', 'ph_value')
        sample_id = data.get('sample_id')
        
        # 获取模型
        active_model = MLModel.query.filter_by(is_active=True).first()
        if not active_model or not os.path.exists(active_model.file_path):
            return jsonify({'error': '模型不可用'}), 400
        
        model = joblib.load(active_model.file_path)
        service = SensitivityService(model)
        
        # 获取基准特征
        if sample_id:
            sample = Sample.query.get(sample_id)
            record = ExperimentRecord.query.filter_by(sample_id=sample.id).order_by(
                ExperimentRecord.created_at.desc()
            ).first() if sample else None
        else:
            record = ExperimentRecord.query.order_by(ExperimentRecord.created_at.desc()).first()
        
        base_features = record.feature_data if record else {}
        
        # 执行分析
        heatmap_data = service.two_feature_heatmap(base_features, feature_x, feature_y, num_points=15)
        single_sensitivities = service.all_features_sensitivity(base_features)
        
        return jsonify({
            'success': True,
            'heatmap': _json_safe(heatmap_data),
            'sensitivities': _json_safe(single_sensitivities)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/case-study/pdf')
@login_required_web
def case_study_pdf():
    """导出案例对比页为 PDF"""
    # 复用 case_study() 的选取逻辑
    reports = OptimizationReport.query.order_by(OptimizationReport.created_at.asc()).all()
    grouped = {}
    for report in reports:
        sample = getattr(report, 'sample', None)
        sid = getattr(sample, 'sample_id', None) if sample else None
        if sid:
            grouped.setdefault(sid, []).append(report)

    case_reports = []
    for sid, items in grouped.items():
        if len(items) > len(case_reports):
            case_reports = items

    if not case_reports:
        flash('暂无足够案例数据，请先进行分析', 'warning')
        return redirect(url_for('web.case_study'))

    case_sample = case_reports[0].sample
    round_timeline = []
    for idx, report in enumerate(case_reports, start=1):
        top3 = (report.top_features or [])[:3]
        round_timeline.append({
            'round': idx,
            'round_label': f'第{idx}轮',
            'probability': round((report.success_probability or 0) * 100, 1),
            'created_at': report.created_at.strftime('%m-%d %H:%M'),
            'top3_features': [
                {
                    'name': item.get('display_name') or item.get('feature', '未知'),
                    'value': item.get('formatted_value') or str(item.get('value', '-')),
                    'contribution': round(item.get('contribution', 0), 3),
                    'impact': 'positive' if item.get('contribution', 0) > 0 else 'negative'
                }
                for item in top3
            ],
            'advice': (report.expert_advice or '无建议').strip()
        })

    first = round_timeline[0]
    last = round_timeline[-1]
    before_after = {
        'first_probability': first['probability'],
        'last_probability': last['probability'],
        'improvement': round(last['probability'] - first['probability'], 1)
    }

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
        trend = '上升' if before_after.get('improvement', 0) >= 0 else '下降'
        top1_names = []
        for item in round_timeline[:3]:
            top1 = ((item.get('top3_features') or [{}])[0] or {}).get('name')
            if top1:
                top1_names.append(top1)
        top1_desc = '、'.join([x for x in top1_names if x]) if top1_names else '关键因子'

        prompt = f"""
请你以“科研论文写作”风格，为以下优化案例生成结构化内容。

【案例信息】
- 样本编号：{getattr(case_sample, 'sample_id', '-')}
- 实验分组：{getattr(case_sample, 'experiment_group', '-')}
- 总轮次：{len(round_timeline)}
- 成功率趋势：{trend}
- 初始成功率：{before_after.get('first_probability', 0):.1f}%
- 最终成功率：{before_after.get('last_probability', 0):.1f}%
- 主要关注因子：{top1_desc}

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

    buffer = pdf_service.build_case_study_pdf(
        case_sample,
        round_timeline,
        before_after=before_after,
        meta=meta,
        abstract_text=abstract_text,
        conclusion_text=conclusion_text,
        keywords=keywords,
        abstract_sections=abstract_sections,
        references=references
    )
    filename = f"case_study_{getattr(case_sample, 'sample_id', 'sample')}.pdf"
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


@bp.route('/batch-compare')
@login_required_web
def batch_compare():
    """批量对比页"""
    samples = Sample.query.order_by(Sample.created_at.desc()).all()
    # 默认展示前 4 个样本
    default_ids = [s.id for s in samples[:4]]
    return render_template('batch_compare.html', samples=samples, default_ids=default_ids)


@bp.route('/api/batch-compare', methods=['POST'])
@login_required_web
def api_batch_compare():
    """AJAX API：批量对比多个样本"""
    try:
        payload = request.get_json() or {}
        sample_ids = payload.get('sample_ids') or []
        sample_ids = [int(x) for x in sample_ids if str(x).isdigit()]
        if not sample_ids:
            return jsonify({'error': '请选择样本'}), 400

        # 拉取样本与最新报告
        samples = Sample.query.filter(Sample.id.in_(sample_ids)).all()
        latest_reports = {}
        reports = OptimizationReport.query.filter(OptimizationReport.sample_id.in_(sample_ids)).order_by(
            OptimizationReport.created_at.desc()
        ).all()
        for r in reports:
            if r.sample_id not in latest_reports:
                latest_reports[r.sample_id] = r

        rows = []
        for s in samples:
            r = latest_reports.get(s.id)
            prob = round((_safe_float(getattr(r, 'success_probability', 0), 0) * 100), 1) if r else 0
            top1 = None
            if r and r.top_features:
                item = (r.top_features or [{}])[0] or {}
                top1 = item.get('display_name') or item.get('feature')
            rows.append({
                'id': s.id,
                'sample_id': s.sample_id,
                'group': s.experiment_group,
                'round': s.experiment_round,
                'probability': prob,
                'top1_feature': top1 or '-'
            })

        # 按成功率降序
        rows.sort(key=lambda x: x['probability'], reverse=True)

        chart = {
            'labels': [x['sample_id'] for x in rows],
            'values': [x['probability'] for x in rows]
        }

        return jsonify({'success': True, 'rows': rows, 'chart': chart})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
