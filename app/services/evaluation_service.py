import numpy as np
from sklearn.metrics import (
    roc_auc_score, f1_score, precision_score, recall_score,
    confusion_matrix, classification_report, roc_curve, precision_recall_curve
)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64

class EvaluationService:
    def __init__(self):
        pass
    
    def comprehensive_evaluation(self, y_true, y_pred, y_pred_proba):
        """综合评估"""
        metrics = {
            'accuracy': self._calculate_accuracy(y_true, y_pred),
            'precision': precision_score(y_true, y_pred, average='binary'),
            'recall': recall_score(y_true, y_pred, average='binary'),
            'f1_score': f1_score(y_true, y_pred, average='binary'),
            'auc': roc_auc_score(y_true, y_pred_proba),
            'confusion_matrix': confusion_matrix(y_true, y_pred).tolist()
        }
        
        # 计算敏感性和特异性
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        metrics['sensitivity'] = tp / (tp + fn) if (tp + fn) > 0 else 0
        metrics['specificity'] = tn / (tn + fp) if (tn + fp) > 0 else 0
        metrics['ppv'] = tp / (tp + fp) if (tp + fp) > 0 else 0  # 阳性预测值
        metrics['npv'] = tn / (tn + fn) if (tn + fn) > 0 else 0  # 阴性预测值
        
        return metrics
    
    def generate_roc_curve(self, y_true, y_pred_proba):
        """生成ROC曲线"""
        fpr, tpr, thresholds = roc_curve(y_true, y_pred_proba)
        auc = roc_auc_score(y_true, y_pred_proba)
        
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot(fpr, tpr, linewidth=2, label=f'ROC (AUC = {auc:.3f})')
        ax.plot([0, 1], [0, 1], 'k--', linewidth=1, label='Random')
        
        ax.set_xlabel('False Positive Rate')
        ax.set_ylabel('True Positive Rate')
        ax.set_title('ROC Curve')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def generate_pr_curve(self, y_true, y_pred_proba):
        """生成Precision-Recall曲线"""
        precision, recall, thresholds = precision_recall_curve(y_true, y_pred_proba)
        
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot(recall, precision, linewidth=2, label='PR Curve')
        
        ax.set_xlabel('Recall')
        ax.set_ylabel('Precision')
        ax.set_title('Precision-Recall Curve')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def generate_confusion_matrix_plot(self, y_true, y_pred):
        """生成混淆矩阵图"""
        cm = confusion_matrix(y_true, y_pred)
        
        fig, ax = plt.subplots(figsize=(6, 6))
        im = ax.imshow(cm, interpolation='nearest', cmap='Blues')
        ax.figure.colorbar(im, ax=ax)
        
        # 添加标签
        ax.set(xticks=np.arange(cm.shape[1]),
               yticks=np.arange(cm.shape[0]),
               xticklabels=['Negative', 'Positive'],
               yticklabels=['Negative', 'Positive'],
               ylabel='True label',
               xlabel='Predicted label')
        
        # 添加数值
        thresh = cm.max() / 2.
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                ax.text(j, i, format(cm[i, j], 'd'),
                       ha="center", va="center",
                       color="white" if cm[i, j] > thresh else "black")
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def calculate_optimal_threshold(self, y_true, y_pred_proba):
        """计算最优阈值"""
        fpr, tpr, thresholds = roc_curve(y_true, y_pred_proba)
        
        # Youden's J statistic
        j_scores = tpr - fpr
        optimal_idx = np.argmax(j_scores)
        optimal_threshold = thresholds[optimal_idx]
        
        return {
            'optimal_threshold': float(optimal_threshold),
            'tpr': float(tpr[optimal_idx]),
            'fpr': float(fpr[optimal_idx]),
            'j_score': float(j_scores[optimal_idx])
        }
    
    def _calculate_accuracy(self, y_true, y_pred):
        """计算准确率"""
        return np.mean(y_true == y_pred)
    
    def _fig_to_base64(self, fig):
        """将matplotlib图转为base64"""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return img_base64

