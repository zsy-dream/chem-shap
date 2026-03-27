# 智析实验 —— 基于SHAP值的化学实验条件归因优化平台

> 用可解释AI取代"盲目试错"，让每一轮实验都有据可依。

## 🚀 项目简介

本系统将博弈论驱动的 **SHAP（SHapley Additive exPlanations）** 算法引入化学/材料实验领域，为研究者提供：

- **实验条件归因分析**：量化反应温度、pH、催化剂用量等每一个条件对实验结果的贡献值
- **智能优化建议**：自动识别 Top-N 关键影响因素并给出调参方向
- **多模型对比**：支持 XGBoost / Random Forest / LightGBM 训练与切换
- **全链路可视化**：瀑布图、力导向图、摘要图、依赖图、ROC曲线、相关性热力图等

**一句话定位**：让实验优化从"经验驱动"升级为"数据驱动 + 可解释AI"。

---

## 📋 核心功能

### 1. 实验样本管理
- 样本基本信息录入（编号、实验轮次、实验分组）
- CSV/Excel 数据批量导入
- 历史记录追踪与分页浏览

### 2. 多模型训练与评估
- **XGBoost**：梯度提升树，结构化数据表现优异
- **Random Forest**：随机森林，鲁棒性强
- **LightGBM**：轻量级GBDT，训练速度快
- 自动数据清洗 → 特征编码 → 标准化 → 交叉验证
- GridSearchCV 超参数自动调优
- 评估指标：AUC / F1 / Precision / Recall / Sensitivity / Specificity / PPV / NPV
- Youden's J 最优阈值计算

### 3. SHAP 归因分析（核心）
- **个体归因**：针对单次实验，计算每个条件的 SHAP 贡献值
- **全局重要性**：分析所有样本的平均特征贡献排序
- **可视化输出**：
  - 瀑布图（Waterfall Plot）：展示从基线到预测值的逐步推导
  - 力导向图（Force Plot）：直观显示正向/负向贡献
  - 摘要图（Summary Plot）：全局特征重要性排序
  - 依赖图（Dependence Plot）：单特征与SHAP值的关系

### 4. 智能报告生成
- 实验结果评级（优秀 / 良好 / 待优化）
- Top 特征贡献排序表
- 针对性优化建议（如"反应温度建议围绕75-90℃梯度优化"）
- 风险仪表盘 / 特征对比图 / 趋势分析图

### 5. 数据可视化仪表盘
- 反应温度 / 催化剂 / pH 趋势折线图
- 实验结果分布饼图（优秀/良好/待优化）
- 多维条件雷达图
- 特征相关性热力图

### 6. RESTful API
- 完整的 API 接口（训练、预测、归因、报告）
- CORS 跨域支持
- 速率限制与错误处理
- 详见 [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

---

## 📊 实验特征字段

| 字段名 | 中文名 | 单位 | 说明 |
|--------|--------|------|------|
| reaction_temperature | 反应温度 | ℃ | 化学反应温度 |
| reaction_time_min | 反应时间 | min | 反应持续时长 |
| ph_value | pH值 | — | 反应溶液酸碱度 |
| catalyst_loading | 催化剂添加量 | % | 催化剂质量百分比 |
| solvent_polarity | 溶剂极性 | — | 溶剂极性指标(0-10) |
| stirring_speed_rpm | 搅拌转速 | rpm | 磁力搅拌转速 |
| reactant_ratio | 反应物配比 | — | 主/副反应物摩尔比 |
| crystallization_time_min | 结晶时间 | min | 产物结晶时间 |
| target | 目标变量 | — | 0=待优化 / 1=达标 |

---

## 🔧 快速开始

### 环境要求
- Python 3.8+
- 8GB+ RAM（推荐）
- 现代浏览器（Chrome / Firefox / Edge）

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 初始化系统

Windows 一键启动：
```bash
完整启动系统.bat
```

或手动执行：
```bash
python init_web_demo.py       # 初始化数据库与演示用户
python create_demo_model.py   # 创建演示模型
python run.py                 # 启动 Web 服务器
```

### 3. 访问系统

浏览器打开：http://localhost:5001

**登录信息：**
- 用户名：`admin`
- 密码：`admin123`

### 4. Docker 部署

```bash
docker-compose build
docker-compose up -d
```

---

## 🎯 使用流程

```
上传实验数据 → 训练模型 → 激活模型 → 选择样本 → SHAP归因分析 → 查看报告与优化建议
```

1. **登录系统** → 使用 admin/admin123 登录
2. **查看样本** → 进入"实验样本管理"，浏览已有数据
3. **训练模型** → 进入"模型管理"，上传CSV数据训练模型
4. **激活模型** → 训练完成后点击"激活"
5. **SHAP分析** → 选择样本和模型，执行归因分析
6. **查看报告** → 在"报告管理"中查看分析结果与优化建议

---

## 📁 项目结构

```
.
├── app/                       # 应用主目录
│   ├── routes/               # 路由模块（Web + API）
│   ├── services/             # 业务逻辑服务
│   ├── templates/            # HTML 模板（Bootstrap 5）
│   ├── utils/                # 工具函数
│   ├── middleware/            # 中间件（速率限制）
│   └── models.py             # 数据模型（ORM）
├── 项目文档/                   # 📄 项目文档专用目录
│   ├── 项目介绍.md            # 详细项目介绍
│   ├── 互联网+大赛商业计划书.md        # 商业计划书（包装版）
│   ├── 互联网+大赛商业计划书_真实版.md  # 商业计划书（真实版）
│   ├── 创新创业项目计划书.md    # 创新创业项目计划书
│   └── 项目文件说明.md         # 项目文件功能说明
├── models/                   # 训练好的模型文件（.pkl）
├── uploads/                  # 上传的数据文件
├── logs/                     # 系统日志
├── tests/                    # 测试文件
├── scripts/                  # 工具脚本
├── config.py                 # 系统配置
├── run.py                    # 启动脚本
├── init_web_demo.py          # 数据库初始化
├── create_demo_model.py      # 创建演示模型
├── sample_data.csv           # 示例数据（10条）
├── sample_data_large.csv     # 示例数据（50条）
└── requirements.txt          # Python 依赖
```

---

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Flask 2.x + Flask-SQLAlchemy + Flask-Login + Flask-CORS |
| 机器学习 | XGBoost / LightGBM / scikit-learn |
| 可解释AI | SHAP（TreeExplainer + KernelExplainer） |
| 数据处理 | Pandas / NumPy / Matplotlib / Seaborn |
| 前端 | Bootstrap 5 + Chart.js + JavaScript |
| 数据库 | SQLite（开发）/ MySQL（生产） |
| 缓存 | Redis（可选） |
| 部署 | Docker + Docker Compose |

---

## 📊 示例数据

| 字段 | sample_data.csv | sample_data_large.csv |
|------|-----------------|----------------------|
| 记录数 | 10 条 | 50 条 |
| 用途 | 快速测试 | 模型训练 |
| 特征数 | 8 个 | 8 个 |

---

## 🐛 故障排除

**模块导入错误**：`pip install -r requirements.txt`

**数据库错误**：
```bash
del instance\shap_chemistry_demo.db   # 删除旧库
python init_web_demo.py              # 重新初始化
```

**端口被占用**：修改 `run.py` 中的端口号，或停止占用 5001 端口的程序。

---

## 📖 相关文档

- [完整使用指南](🎯_完整使用指南.md)
- [API 接口文档](API_DOCUMENTATION.md)
- [版本更新日志](CHANGELOG.md)
- [项目介绍](项目文档/项目介绍.md)
- [互联网+商业计划书](项目文档/互联网+大赛商业计划书.md)
- [创新创业项目计划书](项目文档/创新创业项目计划书.md)
- [项目文件说明](项目文档/项目文件说明.md)

---

## 📄 许可证

查看 [LICENSE](LICENSE) 文件

---

**版本**: 2.0
**更新日期**: 2026-03-11


