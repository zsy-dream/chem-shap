import os

import joblib
import lightgbm as lgb
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GridSearchCV


class ModelService:
    def __init__(self, model_folder='models'):
        self.model_folder = model_folder
        # Vercel 只读文件系统，跳过目录创建
        if not os.environ.get('VERCEL'):
            os.makedirs(model_folder, exist_ok=True)
        self.model = None

    def train_xgboost(self, X_train, y_train, params=None):
        """训练XGBoost模型"""
        if params is None:
            params = {
                'max_depth': 6,
                'learning_rate': 0.1,
                'n_estimators': 100,
                'objective': 'binary:logistic',
                'eval_metric': 'auc'
            }

        self.model = xgb.XGBClassifier(**params)
        self.model.fit(X_train, y_train)
        return self.model

    def train_random_forest(self, X_train, y_train, params=None):
        """训练随机森林模型"""
        if params is None:
            params = {
                'n_estimators': 100,
                'max_depth': 10,
                'random_state': 42
            }

        self.model = RandomForestClassifier(**params)
        self.model.fit(X_train, y_train)
        return self.model

    def train_lightgbm(self, X_train, y_train, params=None):
        """训练LightGBM模型"""
        if params is None:
            params = {
                'num_leaves': 31,
                'learning_rate': 0.05,
                'n_estimators': 100
            }

        self.model = lgb.LGBMClassifier(**params)
        self.model.fit(X_train, y_train)
        return self.model

    def hyperparameter_tuning(self, X_train, y_train, model_type='xgboost'):
        """超参数调优"""
        if model_type == 'xgboost':
            param_grid = {
                'max_depth': [3, 5, 7],
                'learning_rate': [0.01, 0.1, 0.3],
                'n_estimators': [50, 100, 200]
            }
            base_model = xgb.XGBClassifier()
        elif model_type == 'random_forest':
            param_grid = {
                'n_estimators': [50, 100, 200],
                'max_depth': [5, 10, 15],
                'min_samples_split': [2, 5, 10]
            }
            base_model = RandomForestClassifier()
        else:
            raise ValueError(f"Unsupported model type: {model_type}")

        grid_search = GridSearchCV(base_model, param_grid, cv=5, scoring='roc_auc', n_jobs=-1)
        grid_search.fit(X_train, y_train)

        self.model = grid_search.best_estimator_
        return grid_search.best_params_, grid_search.best_score_

    def evaluate_model(self, X_test, y_test):
        """模型评估"""
        if self.model is None:
            raise ValueError("模型未训练")

        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        confusion = confusion_matrix(y_test, y_pred)
        tn, fp, fn, tp = confusion.ravel()

        return {
            'accuracy': accuracy_score(y_test, y_pred),
            'auc': roc_auc_score(y_test, y_pred_proba),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1_score': f1_score(y_test, y_pred),
            'confusion_matrix': confusion.tolist(),
            'sensitivity': tp / (tp + fn) if (tp + fn) else 0,
            'specificity': tn / (tn + fp) if (tn + fp) else 0
        }

    def save_model(self, filename):
        """保存模型"""
        if self.model is None:
            raise ValueError("模型未训练")

        filepath = os.path.join(self.model_folder, filename)
        joblib.dump(self.model, filepath)
        return filepath

    def load_model(self, filename):
        """加载模型"""
        filepath = os.path.join(self.model_folder, filename)
        self.model = joblib.load(filepath)
        return self.model

    def predict(self, X):
        """预测"""
        if self.model is None:
            raise ValueError("模型未加载")

        return self.model.predict_proba(X)[:, 1]

