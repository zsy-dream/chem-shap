from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
import numpy as np

class ReportService:
    def __init__(self):
        self.style = 'seaborn-v0_8-darkgrid'
    
    def generate_success_gauge(self, success_probability):
        """生成成功潜力仪表盘"""
        fig, ax = plt.subplots(figsize=(8, 4))
        
        # 创建半圆仪表盘
        theta = np.linspace(0, np.pi, 100)
        
        # 背景色带
        colors = ['#e74c3c', '#f39c12', '#27ae60']
        boundaries = [0, 0.4, 0.7, 1.0]
        
        for i in range(len(colors)):
            mask = (theta >= boundaries[i] * np.pi) & (theta <= boundaries[i+1] * np.pi)
            ax.fill_between(theta[mask], 0, 1, color=colors[i], alpha=0.3)
        
        # 指针
        angle = success_probability * np.pi
        ax.plot([angle, angle], [0, 0.9], 'k-', linewidth=3)
        ax.plot(angle, 0.9, 'ko', markersize=10)
        
        # 设置
        ax.set_ylim(0, 1)
        ax.set_xlim(0, np.pi)
        ax.axis('off')
        
        # 添加文字
        ax.text(np.pi/2, -0.2, f'{success_probability:.1%}', 
                ha='center', va='top', fontsize=24, fontweight='bold')
        ax.text(0, -0.1, '待优化', ha='left', va='top', fontsize=10)
        ax.text(np.pi, -0.1, '优秀', ha='right', va='top', fontsize=10)
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def generate_feature_comparison(self, sample_features, population_mean):
        """生成特征对比图"""
        features = list(sample_features.keys())
        sample_values = [sample_features[f] for f in features]
        mean_values = [population_mean.get(f, 0) for f in features]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        x = np.arange(len(features))
        width = 0.35
        
        ax.bar(x - width/2, sample_values, width, label='当前样本', color='#3498db')
        ax.bar(x + width/2, mean_values, width, label='历史均值', color='#95a5a6')
        
        ax.set_xlabel('实验特征')
        ax.set_ylabel('数值')
        ax.set_title('样本特征与历史平均对比')
        ax.set_xticks(x)
        ax.set_xticklabels(features, rotation=45, ha='right')
        ax.legend()
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def generate_optimization_trend(self, historical_successes):
        """生成优化趋势图"""
        fig, ax = plt.subplots(figsize=(10, 5))
        
        dates = [r['date'] for r in historical_successes]
        successes = [r['success'] for r in historical_successes]
        
        ax.plot(dates, successes, marker='o', linewidth=2, markersize=8, color='#27ae60')
        ax.fill_between(range(len(dates)), successes, alpha=0.3, color='#27ae60')
        
        # 添加阈值线
        ax.axhline(y=0.75, color='g', linestyle='--', alpha=0.5, label='优秀阈值')
        ax.axhline(y=0.5, color='orange', linestyle='--', alpha=0.5, label='及格阈值')
        
        ax.set_xlabel('迭代日期')
        ax.set_ylabel('成功概率/匹配度')
        ax.set_title('实验优化趋势分析')
        ax.set_xticks(range(len(dates)))
        ax.set_xticklabels(dates, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def generate_feature_correlation_heatmap(self, correlation_matrix, feature_names):
        """生成特征相关性热力图"""
        fig, ax = plt.subplots(figsize=(10, 8))
        
        sns.heatmap(correlation_matrix, 
                   annot=True, 
                   fmt='.2f', 
                   cmap='coolwarm', 
                   center=0,
                   xticklabels=feature_names,
                   yticklabels=feature_names,
                   ax=ax)
        
        ax.set_title('特征相关性热力图')
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def _fig_to_base64(self, fig):
        """将matplotlib图转为base64"""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return img_base64

