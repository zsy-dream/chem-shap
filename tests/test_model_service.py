import pytest
import numpy as np
from sklearn.datasets import make_classification
from app.services.model_service import ModelService

@pytest.fixture
def sample_data():
    X, y = make_classification(n_samples=100, n_features=10, random_state=42)
    return X, y

def test_train_xgboost(sample_data):
    X, y = sample_data
    service = ModelService()
    model = service.train_xgboost(X, y)
    assert model is not None

def test_model_evaluation(sample_data):
    X, y = sample_data
    service = ModelService()
    service.train_xgboost(X, y)
    metrics = service.evaluate_model(X, y)
    
    assert 'auc' in metrics
    assert 'f1_score' in metrics
    assert metrics['auc'] >= 0 and metrics['auc'] <= 1

