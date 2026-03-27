from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator


class SampleCreateSchema(BaseModel):
    sample_id: str = Field(..., min_length=1, max_length=64)
    experiment_round: Optional[int] = Field(None, ge=1, le=1000)
    experiment_group: Optional[str] = Field(None, pattern='^(A|B|M|F|甲组|乙组|A组|B组)$')

    @validator('sample_id')
    def validate_sample_id(cls, value):
        if not value.strip():
            raise ValueError('样本ID不能为空')
        return value.strip()


class ExperimentRecordSchema(BaseModel):
    features: Dict[str, Any]

    @validator('features')
    def validate_features(cls, value):
        if not value:
            raise ValueError('特征数据不能为空')

        if 'reaction_temperature' in value and not (0 <= value['reaction_temperature'] <= 500):
            raise ValueError('反应温度必须在0-500℃之间')

        if 'reaction_time_min' in value and value['reaction_time_min'] <= 0:
            raise ValueError('反应时间必须大于0')

        if 'ph_value' in value and not (0 <= value['ph_value'] <= 14):
            raise ValueError('pH值必须在0-14之间')

        if 'catalyst_loading' in value and value['catalyst_loading'] < 0:
            raise ValueError('催化剂添加量不能为负数')

        if 'stirring_speed_rpm' in value and value['stirring_speed_rpm'] < 0:
            raise ValueError('搅拌转速不能为负数')

        return value


class ModelTrainSchema(BaseModel):
    model_config = {'protected_namespaces': ()}
    name: str = Field(..., min_length=1, max_length=128)
    version: str = Field(default='1.0', max_length=32)
    model_type: str = Field(..., pattern='^(xgboost|random_forest|lightgbm)$')
    data_path: str
    target_column: str
    params: Optional[Dict[str, Any]] = None

    @validator('data_path')
    def validate_data_path(cls, value):
        import os

        if not os.path.exists(value):
            raise ValueError(f'数据文件不存在: {value}')
        return value


class UserRegisterSchema(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field(default='researcher', pattern='^(researcher|admin)$')

    @validator('username')
    def validate_username(cls, value):
        if not value.isalnum() and '_' not in value:
            raise ValueError('用户名只能包含字母、数字和下划线')
        return value


class UserLoginSchema(BaseModel):
    username: str
    password: str

