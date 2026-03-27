"""
Comprehensive initialization for the ChemSHAP demo.
Ensures 16 samples, 16 records, and 8 reports are generated for a 'full' look.
"""
import random
from datetime import datetime, timedelta
from app import create_app, db
from app.models import OptimizationReport, ExperimentRecord, Sample, User, MLModel
from scripts.sample_data_generator import generate_demo_datasets

def _reset_all():
    OptimizationReport.query.delete()
    ExperimentRecord.query.delete()
    Sample.query.delete()
    # Keep models if they are chemistry ones, otherwise clear
    models = MLModel.query.all()
    for m in models:
        if '化学实验' not in m.name:
            db.session.delete(m)
    db.session.commit()

def generate_mock_advice(prob):
    advices = [
        (0.85, "实验环境极佳。建议重点控制反应后段的析出速度，通过程序控温（每小时下降 2℃）来提升晶体纯度。当前催化剂活性处于峰值。"),
        (0.70, "系统识别到反应稳定性良好。SHAP 归因显示 pH 值的正向贡献正在增加，建议微调 pH 至 6.9 以观察是否能突破 80% 的收率关口。"),
        (0.50, "反应效果尚可。但温度波动对产率造成了约 12% 的负向冲击。建议加强热力控制，并延长恒温反应时间约 15 分钟。"),
        (0.30, "当前条件产出受限。关键制约因子是反应时间严重不足。SHAP 模型建议优先将反应时长翻倍，并排查溶剂极性是否匹配当前溶质。"),
        (0.10, "判定结果不理想。模型预测结果显示主要风险来源于催化剂载量过低（贡献度为显著负值）。建议重新核对配比数据，并进行对照组回归。")
    ]
    for threshold, text in advices:
        if prob >= threshold:
            return text
    return advices[-1][1]

def init_demo():
    app = create_app()
    with app.app_context():
        print('Wiping old demo data...')
        _reset_all()

        print('Ensuring demo user exists...')
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()

        # Ensure we have a model
        model = MLModel.query.filter_by(is_active=True).first()
        if not model:
            print('No active model found. Creating a placeholder model record...')
            model = MLModel(
                name='化学实验结果预测模型（演示）',
                version='1.0',
                model_type='xgboost',
                file_path='models/xgboost_demo_model.pkl',
                metrics={'accuracy': 0.85, 'auc': 0.92, 'f1_score': 0.84},
                is_active=True
            )
            db.session.add(model)
            db.session.commit()

        print('\nGenerating datasets...')
        sample_df, _ = generate_demo_datasets()
        rows = sample_df.to_dict(orient='records')

        print('Creating samples, records, and reports...')
        total_samples = 48
        total_reports = 0
        total_records = 0
        group_pool = ['A组', 'B组', '对照组', '优化组', '异常组', '工艺组', '教学组']
        round_pool = [1, 2, 3]

        for i in range(1, total_samples + 1):
            row = rows[(i - 1) % len(rows)].copy()
            s_id = f'EXP-{20260314:08d}-{i:03d}'
            sample = Sample(
                sample_id=s_id,
                experiment_round=random.choice(round_pool),
                experiment_group=random.choice(group_pool)
            )
            db.session.add(sample)
            db.session.flush()

            target = row.pop('target')

            # Create 2 to 6 records for this sample to show history
            num_records = random.randint(2, 6) if i <= 36 else random.randint(1, 3)
            
            base_prob = 0.2 + (random.random() * 0.4)
            if target == 1: base_prob += 0.2

            for rec_idx in range(num_records):
                # Slightly vary features for history
                curr_row = row.copy()
                curr_row['reaction_temperature'] += random.uniform(-2, 2)
                curr_row['ph_value'] += random.uniform(-0.5, 0.5)
                curr_row['catalyst_loading'] += random.uniform(-0.15, 0.15)
                curr_row['reaction_time_min'] += random.uniform(-8, 10)

                record = ExperimentRecord(
                    sample_id=sample.id,
                    feature_data=curr_row,
                    created_at=datetime.utcnow() - timedelta(days=num_records-rec_idx, hours=random.randint(1, 12))
                )
                db.session.add(record)
                db.session.flush()
                total_records += 1

                # Generate report for this record
                # Simulate improvement over time
                drift = 0.10 if sample.experiment_group in ('优化组', '工艺组') else 0.0
                penalty = 0.08 if sample.experiment_group == '异常组' else 0.0
                prob = min(0.98, max(0.02, base_prob + drift - penalty + (rec_idx * 0.12) + random.uniform(-0.06, 0.06)))

                features_pool = [
                    ('reaction_temperature', '反应温度', curr_row.get('reaction_temperature')),
                    ('ph_value', 'pH值', curr_row.get('ph_value')),
                    ('catalyst_loading', '催化剂率', curr_row.get('catalyst_loading')),
                    ('reaction_time_min', '反应时间', curr_row.get('reaction_time_min')),
                    ('solvent_polarity', '溶剂极性', curr_row.get('solvent_polarity'))
                ]
                random.shuffle(features_pool)
                top_fs = []
                for fname, dname, val in features_pool[:4]:
                    contribution = random.uniform(-0.25, 0.35)
                    # if prob is high, make more contributions positive
                    if prob > 0.7 and random.random() > 0.3:
                        contribution = abs(contribution)
                    elif prob < 0.4 and random.random() > 0.3:
                        contribution = -abs(contribution)
                        
                    top_fs.append({
                        'feature': fname,
                        'display_name': dname,
                        'value': val,
                        'contribution': contribution
                    })
                
                report = OptimizationReport(
                    sample_id=sample.id,
                    model_id=model.id,
                    success_probability=prob,
                    shap_values={},
                    top_features=top_fs,
                    expert_advice=generate_mock_advice(prob),
                    created_at=record.created_at + timedelta(minutes=random.randint(2, 10))
                )
                db.session.add(report)
                total_reports += 1

        db.session.commit()
        print(f'Initialization complete! Created {total_samples} samples, {total_records} records, and {total_reports} reports.')

if __name__ == '__main__':
    init_demo()
