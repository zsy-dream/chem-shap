#!/usr/bin/env python
"""检查和补充演示数据，确保部署前数据完整"""
import sys
import os
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import User, Sample, ExperimentRecord, OptimizationReport, MLModel
import pandas as pd

def check_data_status():
    """检查当前数据状态"""
    app = create_app()
    with app.app_context():
        print("="*60)
        print("📊 数据库数据统计")
        print("="*60)
        
        stats = {
            '用户': User.query.count(),
            '样本': Sample.query.count(),
            '实验记录': ExperimentRecord.query.count(),
            '优化报告': OptimizationReport.query.count(),
            '模型': MLModel.query.count()
        }
        
        for k, v in stats.items():
            status = "✅" if v > 0 else "⚠️"
            print(f"{status} {k}: {v}")
        
        # 检查样本详情
        samples = Sample.query.all()
        if samples:
            print(f"\n📋 样本列表（显示前5个）:")
            for s in samples[:5]:
                records = ExperimentRecord.query.filter_by(sample_id=s.id).count()
                reports = OptimizationReport.query.filter_by(sample_id=s.id).count()
                print(f"   • {s.sample_id} | {s.experiment_group} | 记录{records}条 | 报告{reports}份")
        
        return stats, samples

def create_experiment_records(samples, min_records=2, max_records=5):
    """为样本创建实验记录"""
    app = create_app()
    
    # 从生成的 CSV 读取特征数据
    if os.path.exists('training_data.csv'):
        df = pd.read_csv('training_data.csv')
        feature_cols = [c for c in df.columns if c != 'target']
    else:
        feature_cols = ['reaction_temperature', 'reaction_time_min', 'ph_value', 
                       'catalyst_loading', 'solvent_polarity', 'stirring_speed_rpm',
                       'reactant_ratio', 'crystallization_time_min']
    
    with app.app_context():
        created = 0
        for sample in samples:
            # 检查是否已有记录
            existing = ExperimentRecord.query.filter_by(sample_id=sample.id).count()
            if existing >= min_records:
                continue
            
            # 创建实验记录
            for i in range(random.randint(min_records, max_records)):
                record = ExperimentRecord(
                    sample_id=sample.id,
                    feature_data={
                        'reaction_temperature': round(random.uniform(60, 100), 1),
                        'ph_value': round(random.uniform(3.0, 9.0), 1),
                        'catalyst_loading': round(random.uniform(0.5, 3.0), 2),
                        'reaction_time_min': random.randint(30, 120),
                        'stirring_speed_rpm': random.randint(200, 800),
                        'solvent_polarity': round(random.uniform(0.1, 0.9), 1),
                        'reactant_ratio': round(random.uniform(0.8, 1.5), 2),
                        'crystallization_time_min': random.randint(15, 90)
                    },
                    result_status='success' if random.random() > 0.3 else 'failed',
                    notes=f'第{i+1}轮实验记录'
                )
                db.session.add(record)
                created += 1
        
        db.session.commit()
        print(f"\n✅ 创建了 {created} 条实验记录")
        return created

def create_optimization_reports(samples, model_id=2):
    """为样本创建优化报告"""
    app = create_app()
    
    with app.app_context():
        created = 0
        for sample in samples:
            # 检查是否已有报告
            existing = OptimizationReport.query.filter_by(sample_id=sample.id).count()
            if existing > 0:
                continue
            
            # 创建 1-3 份报告
            for round_num in range(1, random.randint(2, 4)):
                prob = round(random.uniform(0.4, 0.95), 3)
                
                # 生成 Top features
                features = [
                    {'feature': 'catalyst_loading', 'display_name': '催化剂添加量', 
                     'value': round(random.uniform(1.5, 3.0), 2), 'contribution': round(random.uniform(0.1, 0.3), 3)},
                    {'feature': 'reaction_temperature', 'display_name': '反应温度',
                     'value': round(random.uniform(70, 90), 1), 'contribution': round(random.uniform(0.05, 0.2), 3)},
                    {'feature': 'ph_value', 'display_name': 'pH值',
                     'value': round(random.uniform(5.0, 7.5), 1), 'contribution': round(random.uniform(0.02, 0.15), 3)}
                ]
                
                report = OptimizationReport(
                    sample_id=sample.id,
                    model_id=model_id,
                    success_probability=prob,
                    top_features=features,
                    expert_advice=f'第{round_num}轮优化建议：调整催化剂用量至{features[0]["value"]}%，可提高成功率至{prob*100:.1f}%'
                )
                db.session.add(report)
                created += 1
        
        db.session.commit()
        print(f"✅ 创建了 {created} 份优化报告")
        return created

def main():
    """主入口"""
    print("🚀 数据完整性检查与补充工具\n")
    
    # 1. 检查当前状态
    stats, samples = check_data_status()
    
    if not samples:
        print("\n⚠️ 没有样本数据，请先运行 init_sample_system.py")
        return
    
    # 2. 补充实验记录
    if stats['实验记录'] < len(samples) * 2:
        print("\n📝 补充实验记录...")
        create_experiment_records(samples)
    else:
        print("\n✅ 实验记录充足")
    
    # 3. 补充优化报告
    if stats['优化报告'] < len(samples):
        print("\n📊 补充优化报告...")
        create_optimization_reports(samples)
    else:
        print("\n✅ 优化报告充足")
    
    # 4. 最终检查
    print("\n" + "="*60)
    print("📊 最终数据状态")
    print("="*60)
    with create_app().app_context():
        for k, v in {
            '用户': User.query.count(),
            '样本': Sample.query.count(),
            '实验记录': ExperimentRecord.query.count(),
            '优化报告': OptimizationReport.query.count(),
            '模型': MLModel.query.count()
        }.items():
            print(f"✅ {k}: {v}")
    
    print("\n" + "="*60)
    print("✨ 数据准备完成，可以部署了！")
    print("="*60)

if __name__ == '__main__':
    main()
