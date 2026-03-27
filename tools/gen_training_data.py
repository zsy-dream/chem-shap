import numpy as np
import pandas as pd

np.random.seed(42)
n_samples = 200

# 特征
temperature = np.random.normal(78, 14, n_samples).clip(30, 130)
time_min = np.random.normal(110, 35, n_samples).clip(20, 240)
ph_value = np.random.normal(6.8, 1.6, n_samples).clip(1, 12)
catalyst_loading = np.random.normal(2.4, 0.9, n_samples).clip(0.1, 5.5)
solvent_polarity = np.random.normal(5.8, 1.7, n_samples).clip(1, 10)
stirring_speed = np.random.normal(520, 130, n_samples).clip(150, 950)
reactant_ratio = np.random.normal(1.08, 0.18, n_samples).clip(0.6, 1.6)
crystallization_time = np.random.normal(85, 28, n_samples).clip(20, 180)

# 稳定性评分 - 优化参数使敏感性更明显
stability_score = (
    3.5  # 增大截距
    - 0.08 * np.abs(temperature - 82)   # 温度敏感度加大
    - 0.03 * np.abs(time_min - 120)     # 时间敏感度
    - 0.6 * np.abs(ph_value - 6.5)      # pH敏感度加大
    - 0.8 * np.abs(catalyst_loading - 2.6)  # 催化剂敏感度最大
    - 0.15 * np.abs(solvent_polarity - 6.0)
    - 0.002 * np.abs(stirring_speed - 540)
    - 2.0 * np.abs(reactant_ratio - 1.05)  # 反应物比例敏感度加大
    - 0.015 * np.abs(crystallization_time - 90)
    + np.random.normal(0, 0.5, n_samples)  # 增大噪声
)

success_probability = 1 / (1 + np.exp(-stability_score))
target = (success_probability >= 0.55).astype(int)

df = pd.DataFrame({
    'reaction_temperature': np.round(temperature, 2),
    'reaction_time_min': np.round(time_min, 2),
    'ph_value': np.round(ph_value, 2),
    'catalyst_loading': np.round(catalyst_loading, 3),
    'solvent_polarity': np.round(solvent_polarity, 2),
    'stirring_speed_rpm': np.round(stirring_speed, 0).astype(int),
    'reactant_ratio': np.round(reactant_ratio, 3),
    'crystallization_time_min': np.round(crystallization_time, 2),
    'target': target
})

df.to_csv('training_data.csv', index=False)
print(f'生成 {n_samples} 条样本')
print(f'成功率分布: {df["target"].value_counts().to_dict()}')
print(f'平均概率: {success_probability.mean():.2f}')
