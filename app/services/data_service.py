import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import LabelEncoder, StandardScaler


class DataService:
    def __init__(self):
        self.scaler = StandardScaler()
        self.label_encoders = {}

    def load_data(self, file_path, file_type='csv'):
        """加载多格式数据"""
        if file_type == 'csv':
            return pd.read_csv(file_path)
        if file_type == 'excel':
            return pd.read_excel(file_path)
        raise ValueError(f"Unsupported file type: {file_type}")

    def clean_data(self, df):
        """数据清洗：处理缺失值和异常值"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        categorical_cols = df.select_dtypes(include=['object']).columns

        if len(numeric_cols) > 0:
            imputer_num = SimpleImputer(strategy='median')
            df[numeric_cols] = imputer_num.fit_transform(df[numeric_cols])

        if len(categorical_cols) > 0:
            imputer_cat = SimpleImputer(strategy='most_frequent')
            df[categorical_cols] = imputer_cat.fit_transform(df[categorical_cols])

        for col in numeric_cols:
            mean = df[col].mean()
            std = df[col].std()
            df[col] = df[col].clip(mean - 3 * std, mean + 3 * std)

        return df

    def encode_features(self, df, categorical_cols):
        """特征编码"""
        df_encoded = df.copy()

        for col in categorical_cols:
            if col not in self.label_encoders:
                self.label_encoders[col] = LabelEncoder()
                df_encoded[col] = self.label_encoders[col].fit_transform(df[col])
            else:
                df_encoded[col] = self.label_encoders[col].transform(df[col])

        return df_encoded

    def normalize_features(self, X, fit=True):
        """特征标准化"""
        if fit:
            return self.scaler.fit_transform(X)
        return self.scaler.transform(X)

    def validate_chemistry_data(self, data):
        """化学实验数据校验"""
        errors = []

        if 'reaction_temperature' in data and not (0 <= data['reaction_temperature'] <= 500):
            errors.append("反应温度必须在0-500℃之间")

        if 'reaction_time_min' in data and data['reaction_time_min'] <= 0:
            errors.append("反应时间必须大于0分钟")

        if 'ph_value' in data and not (0 <= data['ph_value'] <= 14):
            errors.append("pH值必须在0-14之间")

        if 'catalyst_loading' in data and data['catalyst_loading'] < 0:
            errors.append("催化剂添加量不能为负数")

        if 'solvent_polarity' in data and not (0 <= data['solvent_polarity'] <= 10):
            errors.append("溶剂极性指标必须在0-10之间")

        if 'stirring_speed_rpm' in data and data['stirring_speed_rpm'] < 0:
            errors.append("搅拌转速不能为负数")

        if 'reactant_ratio' in data and data['reactant_ratio'] <= 0:
            errors.append("反应物配比必须大于0")

        return len(errors) == 0, errors

