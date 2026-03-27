import numpy as np
import pandas as pd


def generate_sample_chemistry_data(n_samples=120, output_file='sample_data.csv', random_seed=42):
    """生成更适合化学院展示的化学实验 mock 数据"""
    np.random.seed(random_seed)

    temperature = np.random.normal(78, 14, n_samples).clip(30, 130)
    time_min = np.random.normal(110, 35, n_samples).clip(20, 240)
    ph_value = np.random.normal(6.8, 1.6, n_samples).clip(1, 12)
    catalyst_loading = np.random.normal(2.4, 0.9, n_samples).clip(0.1, 5.5)
    solvent_polarity = np.random.normal(5.8, 1.7, n_samples).clip(1, 10)
    stirring_speed = np.random.normal(520, 130, n_samples).clip(150, 950)
    reactant_ratio = np.random.normal(1.08, 0.18, n_samples).clip(0.6, 1.6)
    crystallization_time = np.random.normal(85, 28, n_samples).clip(20, 180)

    stability_score = (
        2.8
        - 0.045 * np.abs(temperature - 82)
        - 0.018 * np.abs(time_min - 120)
        - 0.35 * np.abs(ph_value - 6.5)
        - 0.42 * np.abs(catalyst_loading - 2.6)
        - 0.12 * np.abs(solvent_polarity - 6.0)
        - 0.0012 * np.abs(stirring_speed - 540)
        - 1.4 * np.abs(reactant_ratio - 1.05)
        - 0.01 * np.abs(crystallization_time - 90)
        + np.random.normal(0, 0.35, n_samples)
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

    df.to_csv(output_file, index=False)
    print(f'生成 {n_samples} 条化学实验样本，保存至 {output_file}')
    print(f'优质结果分布: {df["target"].value_counts().to_dict()}')
    return df


def generate_demo_datasets():
    """生成比赛演示所需的小样本与大样本数据文件"""
    small_df = generate_sample_chemistry_data(24, 'sample_data.csv', random_seed=42)
    large_df = generate_sample_chemistry_data(160, 'sample_data_large.csv', random_seed=7)
    return small_df, large_df


def generate_sample_clinical_data(n_samples=120, output_file='sample_data.csv'):
    """保留旧函数名以兼容已有调用"""
    return generate_sample_chemistry_data(n_samples=n_samples, output_file=output_file)


if __name__ == '__main__':
    generate_demo_datasets()

