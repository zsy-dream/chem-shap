import base64
import io
import sys
import types

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

try:
    import torch  # noqa: F401
except Exception:
    sys.modules['torch'] = types.ModuleType('torch')

import shap


class AttributionService:
    def __init__(self, model):
        self.model = model
        self.explainer = None
        self.shap_values = None

    def create_explainer(self, X_background=None):
        """初始化 SHAP 解释器"""
        if hasattr(self.model, 'predict_proba'):
            self.explainer = shap.TreeExplainer(self.model)
        else:
            if X_background is None:
                raise ValueError("KernelExplainer 需要背景数据集（X_background）")
            self.explainer = shap.KernelExplainer(self.model.predict_proba, X_background)
        return self.explainer

    def calculate_shap_values(self, X):
        """计算 SHAP 值"""
        if self.explainer is None:
            raise ValueError("解释器未初始化")

        self.shap_values = self.explainer.shap_values(X)
        if isinstance(self.shap_values, list):
            self.shap_values = self.shap_values[1]
        return self.shap_values

    def get_global_importance(self, X, feature_names):
        """获取全局特征重要性"""
        if self.shap_values is None:
            self.calculate_shap_values(X)

        mean_abs_shap = np.abs(self.shap_values).mean(axis=0)
        importance_dict = dict(zip(feature_names, mean_abs_shap))
        return sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)

    def get_local_explanation(self, X_instance, feature_names):
        """获取单样本解释"""
        if self.explainer is None:
            raise ValueError("解释器未初始化")

        shap_values_instance = self.explainer.shap_values(X_instance)
        if isinstance(shap_values_instance, list):
            shap_values_instance = shap_values_instance[1]

        contributions = {}
        for i, feature in enumerate(feature_names):
            contributions[feature] = float(shap_values_instance[0][i])
        return sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)

    def generate_summary_plot(self, X, feature_names):
        """生成 SHAP 摘要图"""
        if self.shap_values is None:
            self.calculate_shap_values(X)

        plt.figure(figsize=(10, 6))
        shap.summary_plot(self.shap_values, X, feature_names=feature_names, show=False)
        return self._fig_to_base64()

    def generate_waterfall_plot(self, X_instance, feature_names, base_value=None):
        """生成瀑布图"""
        if self.explainer is None:
            raise ValueError("解释器未初始化")

        shap_values_instance = self.explainer.shap_values(X_instance)
        if isinstance(shap_values_instance, list):
            shap_values_instance = shap_values_instance[1]

        if base_value is None:
            base_value = self.explainer.expected_value
            if isinstance(base_value, list):
                base_value = base_value[1]

        plt.figure(figsize=(10, 6))
        shap.waterfall_plot(
            shap.Explanation(
                values=shap_values_instance[0],
                base_values=base_value,
                data=self._get_instance_data(X_instance),
                feature_names=feature_names
            ),
            show=False
        )
        return self._fig_to_base64()

    def generate_force_plot(self, X_instance, feature_names):
        """生成力量图"""
        if self.explainer is None:
            raise ValueError("解释器未初始化")

        shap_values_instance = self.explainer.shap_values(X_instance)
        if isinstance(shap_values_instance, list):
            shap_values_instance = shap_values_instance[1]

        base_value = self.explainer.expected_value
        if isinstance(base_value, list):
            base_value = base_value[1]

        shap.force_plot(
            base_value,
            shap_values_instance[0],
            self._get_instance_data(X_instance),
            feature_names=feature_names,
            matplotlib=True,
            show=False
        )
        return self._fig_to_base64()

    def generate_dependence_plot(self, X, feature_name, feature_names, interaction_feature=None):
        """生成依赖图"""
        if self.shap_values is None:
            self.calculate_shap_values(X)

        feature_idx = feature_names.index(feature_name)
        plt.figure(figsize=(10, 6))
        shap.dependence_plot(
            feature_idx,
            self.shap_values,
            X,
            feature_names=feature_names,
            interaction_index=interaction_feature,
            show=False
        )
        return self._fig_to_base64()

    def _fig_to_base64(self):
        """将 matplotlib 图表转换为 base64"""
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()
        return img_base64

    def _get_instance_data(self, X_instance):
        if hasattr(X_instance, 'iloc'):
            return X_instance.iloc[0].values
        return X_instance[0]

