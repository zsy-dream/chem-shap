#!/usr/bin/env python
"""初始化化学实验分析平台示例系统"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import User, Sample, ExperimentRecord
from scripts.sample_data_generator import generate_demo_datasets
import pandas as pd

def init_database():
    """初始化数据库架构"""
    print("正在初始化数据库...")
    app = create_app()
    
    with app.app_context():
        db.create_all()
        print("✓ 数据库表结构同步成功")
        
        # 创建超级管理员
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            print("✓ 管理员账户 (admin) 已就绪")
        
        # 创建科研人员账户
        if not User.query.filter_by(username='researcher').first():
            researcher = User(username='researcher', role='researcher')
            researcher.set_password('researcher123')
            db.session.add(researcher)
            researcher_old = User.query.filter_by(username='doctor').first()
            if researcher_old:
                db.session.delete(researcher_old)
            print("✓ 实验研究员账户 (researcher) 已就绪")
        
        db.session.commit()

def create_sample_experiments():
    """创建演示用实验样本"""
    print("\n正在生成演示实验样本...")
    app = create_app()
    
    with app.app_context():
        # 检查是否已有样本数据
        if Sample.query.count() > 0:
            print("⚠ 检测到已有样本数据，跳过自动生成")
            return
        
        # 创建12个演示样本
        for i in range(1, 13):
            sample = Sample(
                sample_id=f'EXP-{str(i).zfill(4)}',
                experiment_round=1,
                experiment_group='A组' if i % 2 == 0 else 'B组'
            )
            db.session.add(sample)
        
        db.session.commit()
        print(f"✓ 成功创建 {Sample.query.count()} 个演示实验样本")

def generate_training_data():
    """生成化学实验模拟训练数据集"""
    print("\n生成训练数据集...")
    
    if os.path.exists('sample_data.csv') and os.path.exists('sample_data_large.csv'):
        print("⚠ 训练数据文件已存在，跳过生成步骤")
        return
    
    generate_demo_datasets()
    print("✓ 化学实验数据集 (sample_data.csv, sample_data_large.csv) 生成成功")

def main():
    """初始化脚本入口"""
    print("=" * 60)
    print("智析实验 · 化学实验归因分析平台 初始化工具")
    print("=" * 60)
    print()
    
    try:
        # 1. 初始化数据库
        init_database()
        
        # 2. 创建演示样本
        create_sample_experiments()
        
        # 3. 生成训练数据
        generate_training_data()
        
        print("\n" + "=" * 60)
        print("✓ 智析实验系统环境初始化完成")
        print("=" * 60)
        print("\n预设登录账号:")
        print("  管理员: admin / admin123")
        print("  研究员: researcher / researcher123")
        print("\n常用命令:")
        print("  1. 启动服务: python run.py")
        print("  2. 环境清理: del instance\\*.db")
        print()
        
        return 0
    except Exception as e:
        print(f"\n✗ 初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())

