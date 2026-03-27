"""Create a stronger chemistry demo model with clearer feature sensitivity."""

import os

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from app import create_app, db
from app.models import MLModel
from app.services.data_service import DataService
from app.services.model_service import ModelService


def _generate_strong_demo_dataset(n_samples: int = 240, random_seed: int = 42) -> pd.DataFrame:
    np.random.seed(random_seed)

    temperature = np.random.normal(78, 14, n_samples).clip(30, 130)
    time_min = np.random.normal(110, 35, n_samples).clip(20, 240)
    ph_value = np.random.normal(6.8, 1.6, n_samples).clip(1, 12)
    catalyst_loading = np.random.normal(2.4, 0.9, n_samples).clip(0.1, 5.5)
    solvent_polarity = np.random.normal(5.8, 1.7, n_samples).clip(1, 10)
    stirring_speed = np.random.normal(520, 130, n_samples).clip(150, 950)
    reactant_ratio = np.random.normal(1.08, 0.18, n_samples).clip(0.6, 1.6)
    crystallization_time = np.random.normal(85, 28, n_samples).clip(20, 180)

    # Make the relationship clearer than the default sample generator
    stability_score = (
        3.5
        - 0.08 * np.abs(temperature - 82)
        - 0.03 * np.abs(time_min - 120)
        - 0.60 * np.abs(ph_value - 6.5)
        - 0.80 * np.abs(catalyst_loading - 2.6)
        - 0.15 * np.abs(solvent_polarity - 6.0)
        - 0.002 * np.abs(stirring_speed - 540)
        - 2.00 * np.abs(reactant_ratio - 1.05)
        - 0.015 * np.abs(crystallization_time - 90)
        + np.random.normal(0, 0.50, n_samples)
    )

    success_probability = 1 / (1 + np.exp(-stability_score))
    target = (success_probability >= 0.55).astype(int)

    df = pd.DataFrame(
        {
            "reaction_temperature": np.round(temperature, 2),
            "reaction_time_min": np.round(time_min, 2),
            "ph_value": np.round(ph_value, 2),
            "catalyst_loading": np.round(catalyst_loading, 3),
            "solvent_polarity": np.round(solvent_polarity, 2),
            "stirring_speed_rpm": np.round(stirring_speed, 0).astype(int),
            "reactant_ratio": np.round(reactant_ratio, 3),
            "crystallization_time_min": np.round(crystallization_time, 2),
            "target": target,
        }
    )

    return df


def create_strong_demo_model():
    app = create_app()
    with app.app_context():
        os.makedirs("uploads", exist_ok=True)
        os.makedirs("models", exist_ok=True)

        df = _generate_strong_demo_dataset(n_samples=240, random_seed=42)
        df.to_csv("training_data.csv", index=False)

        model_service = ModelService()
        data_service = DataService()

        df_clean = data_service.clean_data(df)
        X = df_clean.drop(columns=["target"])
        y = df_clean["target"]

        categorical_cols = X.select_dtypes(include=["object"]).columns.tolist()
        X_encoded = data_service.encode_features(X, categorical_cols)
        X_normalized = data_service.normalize_features(X_encoded)

        X_train, X_test, y_train, y_test = train_test_split(
            X_normalized, y, test_size=0.2, random_state=42
        )

        model_service.train_xgboost(X_train, y_train)
        metrics = model_service.evaluate_model(X_test, y_test)

        model_filename = "xgboost_strong_demo_model.pkl"
        model_filepath = model_service.save_model(model_filename)

        # deactivate all models first
        MLModel.query.update({MLModel.is_active: False})
        db.session.commit()

        ml_model = MLModel(
            name="化学实验结果预测模型（强相关演示）",
            version="1.0",
            model_type="xgboost",
            file_path=model_filepath,
            metrics=metrics,
            is_active=True,
        )
        db.session.add(ml_model)
        db.session.commit()

        print("=" * 60)
        print("Strong demo model created & activated")
        print("=" * 60)
        print(f"ID: {ml_model.id}")
        print(f"Name: {ml_model.name}")
        print(f"Model file: {ml_model.file_path}")
        print(f"Accuracy: {metrics.get('accuracy', 0) * 100:.2f}%")
        print(f"AUC: {metrics.get('auc', 0):.3f}")
        print(f"Class balance: {df['target'].value_counts().to_dict()}")
        print("Saved dataset: training_data.csv")
        print("=" * 60)


if __name__ == "__main__":
    create_strong_demo_model()
