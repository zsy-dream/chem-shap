"""敏感性分析服务 - 分析特征参数对成功率的影响"""
import numpy as np
import pandas as pd


class SensitivityService:
    """敏感性分析服务"""
    
    # 特征定义（与系统其他部分保持一致）
    FEATURE_CONFIG = {
        'reaction_temperature': {
            'label': '反应温度',
            'unit': '°C',
            'range': [60, 100],
            'step': 5,
            'default': 80
        },
        'ph_value': {
            'label': 'pH值',
            'unit': '',
            'range': [3.0, 9.0],
            'step': 0.5,
            'default': 6.0
        },
        'catalyst_loading': {
            'label': '催化剂添加量',
            'unit': '%',
            'range': [0.5, 3.0],
            'step': 0.25,
            'default': 1.5
        },
        'reaction_time_min': {
            'label': '反应时间',
            'unit': 'min',
            'range': [30, 120],
            'step': 10,
            'default': 60
        },
        'stirring_speed_rpm': {
            'label': '搅拌转速',
            'unit': 'rpm',
            'range': [200, 800],
            'step': 50,
            'default': 400
        },
        'solvent_polarity': {
            'label': '溶剂极性',
            'unit': '',
            'range': [0.1, 0.9],
            'step': 0.1,
            'default': 0.5
        },
        'reactant_ratio': {
            'label': '反应物比例',
            'unit': '',
            'range': [0.8, 1.5],
            'step': 0.1,
            'default': 1.0
        },
        'crystallization_time_min': {
            'label': '结晶时间',
            'unit': 'min',
            'range': [15, 90],
            'step': 5,
            'default': 30
        }
    }
    
    def __init__(self, model):
        """
        初始化敏感性分析服务
        :param model: 训练好的机器学习模型
        """
        self.model = model
        self.feature_names = None
        if hasattr(model, 'feature_names_in_'):
            self.feature_names = list(model.feature_names_in_)
        
    def single_feature_sensitivity(self, base_features, feature_name, num_points=20):
        """
        单因素敏感性分析
        :param base_features: 基准特征值字典
        :param feature_name: 要分析的特征名
        :param num_points: 采样点数
        :return: 特征值范围和对应成功率列表
        """
        if feature_name not in self.FEATURE_CONFIG:
            raise ValueError(f"未知的特征: {feature_name}")
        
        config = self.FEATURE_CONFIG[feature_name]
        feature_range = np.linspace(config['range'][0], config['range'][1], num_points)
        
        probabilities = []
        for value in feature_range:
            features = base_features.copy()
            features[feature_name] = value
            
            # 构建输入数据
            X = self._build_input(features)
            
            # 预测
            if hasattr(self.model, 'predict_proba'):
                prob = self.model.predict_proba(X)[0][1]
            else:
                prob = float(self.model.predict(X)[0])
            
            probabilities.append(round(prob * 100, 2))
        
        return {
            'feature': feature_name,
            'label': config['label'],
            'unit': config['unit'],
            'values': feature_range.tolist(),
            'probabilities': probabilities,
            'optimal_value': feature_range[np.argmax(probabilities)].item(),
            'max_probability': max(probabilities),
            'min_probability': min(probabilities),
            'sensitivity_score': max(probabilities) - min(probabilities)  # 敏感性得分
        }
    
    def two_feature_heatmap(self, base_features, feature_x, feature_y, num_points=15):
        """
        双因素热力图分析
        :param base_features: 基准特征值字典
        :param feature_x: X轴特征名
        :param feature_y: Y轴特征名
        :param num_points: 每轴采样点数
        :return: 热力图数据
        """
        if feature_x not in self.FEATURE_CONFIG or feature_y not in self.FEATURE_CONFIG:
            raise ValueError("未知的特征")
        
        config_x = self.FEATURE_CONFIG[feature_x]
        config_y = self.FEATURE_CONFIG[feature_y]
        
        values_x = np.linspace(config_x['range'][0], config_x['range'][1], num_points)
        values_y = np.linspace(config_y['range'][0], config_y['range'][1], num_points)
        
        heatmap_matrix = []
        max_prob = 0
        optimal_point = None
        
        for y in values_y:
            row = []
            for x in values_x:
                features = base_features.copy()
                features[feature_x] = x
                features[feature_y] = y
                
                X = self._build_input(features)
                
                if hasattr(self.model, 'predict_proba'):
                    prob = self.model.predict_proba(X)[0][1] * 100
                else:
                    prob = float(self.model.predict(X)[0]) * 100
                
                row.append(round(prob, 2))
                
                if prob > max_prob:
                    max_prob = prob
                    optimal_point = {feature_x: x, feature_y: y}
            
            heatmap_matrix.append(row)
        
        return {
            'feature_x': feature_x,
            'feature_y': feature_y,
            'label_x': config_x['label'],
            'label_y': config_y['label'],
            'unit_x': config_x['unit'],
            'unit_y': config_y['unit'],
            'values_x': values_x.tolist(),
            'values_y': values_y.tolist(),
            'heatmap': heatmap_matrix,
            'optimal_point': optimal_point,
            'max_probability': round(max_prob, 2),
            'probability_range': [round(min(min(row) for row in heatmap_matrix), 2),
                                  round(max(max(row) for row in heatmap_matrix), 2)]
        }
    
    def all_features_sensitivity(self, base_features):
        """
        分析所有特征的敏感性
        :param base_features: 基准特征值
        :return: 所有特征的敏感性排名
        """
        results = []
        for feature_name in self.FEATURE_CONFIG.keys():
            try:
                result = self.single_feature_sensitivity(base_features, feature_name, num_points=15)
                results.append({
                    'feature': feature_name,
                    'label': result['label'],
                    'unit': result['unit'],
                    'sensitivity_score': result['sensitivity_score'],
                    'optimal_value': result['optimal_value'],
                    'max_probability': result['max_probability']
                })
            except Exception as e:
                print(f"分析特征 {feature_name} 时出错: {e}")
                continue
        
        # 按敏感性得分排序
        results.sort(key=lambda x: x['sensitivity_score'], reverse=True)
        return results
    
    def _build_input(self, features):
        """构建模型输入"""
        # 确保所有特征都存在
        for key in self.FEATURE_CONFIG.keys():
            if key not in features:
                features[key] = self.FEATURE_CONFIG[key]['default']
        
        # 创建DataFrame
        if self.feature_names:
            # 按模型训练时的特征顺序
            data = {name: features.get(name, self.FEATURE_CONFIG[name]['default']) 
                   for name in self.feature_names}
            X = pd.DataFrame([data])
        else:
            X = pd.DataFrame([features])
        
        return X
