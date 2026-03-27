import pytest
import pandas as pd
import numpy as np
from app.services.data_service import DataService

def test_clean_data():
    """测试数据清洗功能"""
    data_service = DataService()
    
    # 创建测试数据
    df = pd.DataFrame({
        'age': [25, np.nan, 45, 60],
        'bmi': [22.5, 28.0, np.nan, 32.0],
        'gender': ['M', 'F', np.nan, 'M']
    })
    
    # 清洗数据
    df_clean = data_service.clean_data(df)
    
    # 验证没有缺失值
    assert df_clean.isnull().sum().sum() == 0

def test_validate_medical_data():
    """测试医学数据校验"""
    data_service = DataService()
    
    # 有效数据
    valid_data = {
        'age': 45,
        'blood_pressure_systolic': 120,
        'blood_pressure_diastolic': 80
    }
    is_valid, errors = data_service.validate_medical_data(valid_data)
    assert is_valid == True
    
    # 无效数据
    invalid_data = {
        'age': -5,
        'blood_pressure_systolic': -10
    }
    is_valid, errors = data_service.validate_medical_data(invalid_data)
    assert is_valid == False
    assert len(errors) > 0

