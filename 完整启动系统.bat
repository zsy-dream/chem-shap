@echo off
chcp 65001 >nul
echo ========================================
echo   智析实验 - 化学实验条件归因分析系统
echo ========================================
echo.

echo [1/3] 初始化数据库与演示样本...
py init_web_demo.py
if errorlevel 1 (
    echo ❌ 数据库初始化失败
    pause
    exit /b 1
)

echo.
echo [2/3] 预训练演示模型 (XGBoost)...
py create_demo_model.py
if errorlevel 1 (
    echo ❌ 模型创建失败
    pause
    exit /b 1
)

echo.
echo [3/3] 正在启动 Web 服务器...
echo.
echo ========================================
echo   ✓ 智析实验系统准备完成！
echo ========================================
echo.
echo   访问地址: http://localhost:5001
echo   用户名: admin
echo   密码: admin123
echo.
echo   核心功能:
echo   - 样本管理: 查看化学实验参数记录
echo   - 模型管理: 支持 XGBoost/随机森林/LGBM
echo   - SHAP分析: 归因分析并生成 AI 优化建议
echo   - 报告管理: 导出详细实验分析报告
echo.
echo   按 Ctrl+C 停止服务器
echo ========================================
echo.

py run.py

pause
