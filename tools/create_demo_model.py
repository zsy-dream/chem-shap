"""
Create the chemistry demo model.
"""
import os

import pandas as pd
from sklearn.model_selection import train_test_split

from app import create_app, db
from app.models import MLModel
from app.services.data_service import DataService
from app.services.model_service import ModelService
from scripts.sample_data_generator import generate_demo_datasets


def _should_reset_models():
    model = MLModel.query.first()
    if not model:
        return True
    return '化学实验' not in model.name


def create_demo_model():
    app = create_app()
    with app.app_context():
        print('=' * 60)
        print('Creating demo model...')
        print('=' * 60)

        if _should_reset_models():
            print('\nLegacy medical model detected; rebuilding chemistry model...')
            MLModel.query.delete()
            db.session.commit()

        if MLModel.query.count() > 0:
            print(f'\nChemistry model already exists: {MLModel.query.count()}')
            return

        try:
            model_service = ModelService()
            data_service = DataService()

            print('\n[1/5] Loading sample data...')
            if not os.path.exists('sample_data.csv'):
                generate_demo_datasets()
            df = pd.read_csv('sample_data.csv')
            if 'target' not in df.columns or 'reaction_temperature' not in df.columns:
                generate_demo_datasets()
                df = pd.read_csv('sample_data.csv')
            print(f'Loaded {len(df)} rows')

            print('\n[2/5] Cleaning data...')
            df_clean = data_service.clean_data(df)
            X = df_clean.drop(columns=['target'])
            y = df_clean['target']
            print(f'Feature count: {X.shape[1]}')
            print(f'Sample count: {X.shape[0]}')

            categorical_cols = X.select_dtypes(include=['object']).columns.tolist()
            X_encoded = data_service.encode_features(X, categorical_cols)
            X_normalized = data_service.normalize_features(X_encoded)

            print('\n[3/5] Splitting train/test...')
            X_train, X_test, y_train, y_test = train_test_split(X_normalized, y, test_size=0.2, random_state=42)
            print(f'Train size: {len(X_train)}')
            print(f'Test size: {len(X_test)}')

            print('\n[4/5] Training XGBoost model...')
            model_service.train_xgboost(X_train, y_train)
            print('Training complete')

            print('\n[5/5] Evaluating model...')
            metrics = model_service.evaluate_model(X_test, y_test)
            print(f"Accuracy: {metrics.get('accuracy', 0) * 100:.2f}%")
            print(f"AUC: {metrics.get('auc', 0):.3f}")
            print(f"F1: {metrics.get('f1_score', 0):.3f}")

            model_filename = 'xgboost_demo_model.pkl'
            model_filepath = model_service.save_model(model_filename)

            ml_model = MLModel(
                name='化学实验结果预测模型（演示）',
                version='1.0',
                model_type='xgboost',
                file_path=model_filepath,
                metrics=metrics,
                is_active=True
            )
            db.session.add(ml_model)
            db.session.commit()

            print('\n' + '=' * 60)
            print('Chemistry demo model created successfully')
            print('=' * 60)
            print(f'ID: {ml_model.id}')
            print(f'Name: {ml_model.name}')
            print(f'Type: {ml_model.model_type}')
            print(f"Accuracy: {metrics.get('accuracy', 0) * 100:.2f}%")
            print('Status: active')
            print('=' * 60)
        except Exception as error:
            print(f'\nModel creation failed: {error}')
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    create_demo_model()

