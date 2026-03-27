@echo off
chcp 65001 >nul
setlocal

echo ============================================================
echo   SHAP化学实验归因平台 - EXE 打包脚本 (虚拟环境无污染版)
echo ============================================================
echo.

echo [1/6] 检查 Python ...
python --version
if errorlevel 1 (
    echo [ERROR] 未找到 Python，请先安装配置环境变量后重试。
    pause
    exit /b 1
)

echo.
echo [2/6] 创建并准备干净的虚拟环境 (可避免依赖冲突造成打包失败或包体积过大) ...
if not exist "venv_build" (
    python -m venv venv_build
    call venv_build\Scripts\activate.bat
    python -m ensurepip --upgrade
) else (
    call venv_build\Scripts\activate.bat
)

echo.
echo [3/6] 安装必需的依赖库和打包工具 ...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller
if errorlevel 1 (
    echo [ERROR] 依赖安装失败。
    pause
    exit /b 1
)

echo.
echo [4/6] 准备演示数据和演示模型 ...
set PYTHONPATH=.
python scripts\init_web_demo.py
if errorlevel 1 (
    echo [WARN] 演示数据初始化失败，继续打包...
)
python scripts\create_demo_model.py
if errorlevel 1 (
    echo [WARN] 演示模型创建失败，继续打包...
)

echo.
echo [5/6] 清理旧的构建文件 ...
if exist build rd /s /q build
if exist dist\ChemSHAPDemo rd /s /q dist\ChemSHAPDemo

echo.
echo [6/6] 开始打包 EXE (过程会占用较多内存，请耐心等待) ...
set PYTHONPATH=.
python -m PyInstaller --noconfirm ChemSHAPDemo.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller 打包失败。
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   打包完成！
echo ============================================================
echo 输出目录: dist\ChemSHAPDemo
echo 可执行文件: dist\ChemSHAPDemo\ChemSHAPDemo.exe
echo.
echo 发送给别人时，请把整个 dist\ChemSHAPDemo 文件夹压缩后发送，
echo 【绝对不要】只单独发送 exe 文件。
echo ============================================================
