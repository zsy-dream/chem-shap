# API 接口文档

## 基础信息

- 基础URL: `http://localhost:5000/api`
- 认证方式: Session-based (Flask-Login)
- 响应格式: JSON

## 认证接口

### 1. 用户注册

**POST** `/auth/register`

请求体:
```json
{
  "username": "researcher1",
  "password": "password123",
  "role": "researcher"
}
```

响应:
```json
{
  "message": "注册成功",
  "user_id": 1
}
```

### 2. 用户登录

**POST** `/auth/login`

请求体:
```json
{
  "username": "researcher1",
  "password": "password123"
}
```

响应:
```json
{
  "message": "登录成功",
  "user": {
    "id": 1,
    "username": "researcher1",
    "role": "researcher"
  }
}
```

### 3. 用户登出

**POST** `/auth/logout`

响应:
```json
{
  "message": "登出成功"
}
```

## 数据管理接口

### 4. 上传数据文件

**POST** `/data/upload`

请求: multipart/form-data
- file: CSV或Excel文件

响应:
```json
{
  "message": "文件上传成功",
  "rows": 1000,
  "columns": ["reaction_temperature", "catalyst_loading", "ph_value", ...]
}
```

### 5. 获取样本列表

**GET** `/data/Samples`

响应:
```json
[
  {
    "id": 1,
    "sample_id": "EXP-0001",
    "reaction_temperature": 75,
    "experiment_group": "A组",
    "created_at": "2026-01-01T00:00:00"
  }
]
```

### 6. 创建样本

**POST** `/data/Samples`

请求体:
```json
{
  "sample_id": "EXP-0001",
  "experiment_round": 1,
  "experiment_group": "A组"
}
```

## 模型接口

### 7. 训练模型

**POST** `/model/train`

请求体:
```json
{
  "name": "catalyst_efficiency_model",
  "version": "1.0",
  "model_type": "xgboost",
  "data_path": "data/sample_data_large.csv",
  "target_column": "target",
  "params": {
    "max_depth": 6,
    "learning_rate": 0.1
  }
}
```

响应:
```json
{
  "message": "模型训练成功",
  "model_id": 1,
  "metrics": {
    "auc": 0.85,
    "f1_score": 0.78,
    "sensitivity": 0.82,
    "specificity": 0.76
  }
}
```

### 8. 获取模型列表

**GET** `/model/models`

### 9. 激活模型

**POST** `/model/models/{model_id}/activate`

### 10. 预测

**POST** `/model/predict`

请求体:
```json
{
  "features": {
    "reaction_temperature": 75.5,
    "catalyst_loading": 2.5,
    "reaction_time_min": 120,
    "ph_value": 6.8
  }
}
```

## 分析接口

### 11. SHAP分析

**POST** `/analysis/shap`

请求体:
```json
{
  "sample_id": 1,
  "model_id": 1,
  "features": {
    "reaction_temperature": 75.5,
    "catalyst_loading": 2.5,
    "ph_value": 6.8
  }
}
```

响应:
```json
{
  "success_probability": 0.75,
  "shap_values": {
    "reaction_temperature": 0.12,
    "catalyst_loading": 0.08,
    "ph_value": 0.15
  },
  "top_features": [
    {"feature": "ph_value", "contribution": 0.15},
    {"feature": "reaction_temperature", "contribution": 0.12},
    {"feature": "catalyst_loading", "contribution": 0.08}
  ],
  "visualizations": {
    "waterfall_plot": "base64_image_data",
    "force_plot": "base64_image_data"
  }
}
```

### 12. 全局特征重要性

**POST** `/analysis/global-importance`

### 13. 获取样本报告

**GET** `/analysis/reports/{sample_id}`

## 报告接口

### 14. 生成报告

**GET** `/report/generate/{report_id}`

### 15. 导出报告

**GET** `/report/export/{report_id}`

## 健康检查接口

### 16. 系统状态

**GET** `/health/status`

响应:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00",
  "services": {
    "database": "healthy",
    "redis": "healthy"
  }
}
```

### 17. 系统统计

**GET** `/health/stats`

响应:
```json
{
  "users": 10,
  "Samples": 500,
  "models": 5,
  "active_models": 1
}
```

## 错误响应

所有错误响应格式:
```json
{
  "error": "错误类型",
  "message": "详细错误信息"
}
```

常见HTTP状态码:
- 200: 成功
- 201: 创建成功
- 400: 请求参数错误
- 401: 未认证
- 403: 权限不足
- 404: 资源未找到
- 500: 服务器内部错误


