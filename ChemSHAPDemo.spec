# -*- mode: python ; coding: utf-8 -*-

import os
import sys

block_cipher = None

# 获取项目根目录
project_root = os.path.dirname(os.path.abspath('launcher.py'))

# 资源文件列表 (源路径, 目标路径)
added_files = [
    ('app/templates', 'app/templates'),
    ('app/static', 'app/static'),
    ('data', 'data'),
    ('models', 'models'),
    ('instance', 'instance'),
    ('.env.example', '.'),
    ('sample_data.csv', '.'),
    ('sample_data_large.csv', '.'),
    # 强制包含这些工具，因为 launcher 会引用
    ('tools', 'tools'),
]

# 检查是否存在相关资源，不存在则过滤掉
valid_assets = []
for src, dst in added_files:
    if os.path.exists(os.path.join(project_root, src)):
        valid_assets.append((src, dst))

a = Analysis(
    ['launcher.py'],
    pathex=[project_root],
    binaries=[],
    datas=valid_assets,
    hiddenimports=[
        'flask', 'flask_sqlalchemy', 'flask_login', 'flask_cors', 'flask_limiter',
        'pandas', 'numpy', 'sklearn', 'xgboost', 'lightgbm', 'shap', 'matplotlib',
        'seaborn', 'reportlab', 'pymysql', 'redis', 'dotenv', 'joblib', 'pydantic'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'torchaudio', 'transformers', 'tensorflow', 'tensorboard', 'notebook', 'jinja2.tests', 'IPython'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='智析实验归因系统',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # 开启终端以查看启动信息
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='app/static/img/favicon.ico',  # 如果有图标可以取消注释
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='智析实验归因系统',
)
