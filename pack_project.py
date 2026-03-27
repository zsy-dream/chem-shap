"""
项目打包脚本 - 生成干净的项目交付压缩包

自动排除敏感文件（.env、数据库）、缓存（__pycache__）、
构建产物（build/dist）等，生成可安全分享的 zip 包。
"""
import os
import zipfile
import datetime
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# NOTE: 项目根目录为脚本所在目录
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# NOTE: 需要排除的目录和文件列表，防止泄露密钥和无用文件
EXCLUDE_DIRS: set[str] = {
    ".git",
    "__pycache__",
    "build",
    "dist",
    "instance",
    "cachedir",
    "logs",
    "uploads",
    "venv",
    "env",
    ".vscode",
    ".idea",
    "node_modules",
    ".agents",
}

EXCLUDE_FILES: set[str] = {
    ".env",           # 含 API 密钥，绝不可泄露
    "pack_project.py",  # 打包脚本本身不需要
    ".DS_Store",
    "Thumbs.db",
}

EXCLUDE_EXTENSIONS: set[str] = {
    ".pyc",
    ".pyo",
    ".log",
    ".db",
    ".sqlite",
}


def should_exclude(root: str, name: str, is_dir: bool) -> bool:
    """
    判断文件/目录是否应被排除

    Args:
        root: 当前遍历的父目录路径
        name: 文件或目录名
        is_dir: 是否为目录

    Returns:
        True 表示应排除
    """
    if is_dir:
        return name in EXCLUDE_DIRS

    if name in EXCLUDE_FILES:
        return True

    _, ext = os.path.splitext(name)
    if ext.lower() in EXCLUDE_EXTENSIONS:
        return True

    return False


def pack_project() -> str:
    """
    将项目打包为 zip 文件，输出到桌面

    Returns:
        生成的 zip 文件路径
    """
    today = datetime.date.today().strftime("%Y%m%d")
    zip_name = f"智析实验_项目交付包_{today}.zip"

    # NOTE: 优先输出到桌面，找不到桌面则输出到项目同级目录
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if os.path.isdir(desktop):
        output_path = os.path.join(desktop, zip_name)
    else:
        output_path = os.path.join(os.path.dirname(PROJECT_DIR), zip_name)

    project_name = os.path.basename(PROJECT_DIR)
    file_count = 0

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(PROJECT_DIR):
            # NOTE: 原地修改 dirs 列表可阻止 os.walk 进入被排除的子目录
            dirs[:] = [
                d for d in dirs
                if not should_exclude(root, d, is_dir=True)
            ]

            for filename in files:
                if should_exclude(root, filename, is_dir=False):
                    continue

                file_path = os.path.join(root, filename)
                # 保持压缩包内的相对路径结构
                arcname = os.path.join(
                    project_name,
                    os.path.relpath(file_path, PROJECT_DIR),
                )
                zf.write(file_path, arcname)
                file_count += 1

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    logger.info("=" * 50)
    logger.info("✅ 打包完成！")
    logger.info(f"   文件数量: {file_count} 个")
    logger.info(f"   压缩大小: {size_mb:.2f} MB")
    logger.info(f"   输出路径: {output_path}")
    logger.info("=" * 50)
    logger.info("")
    logger.info("⚠️  已自动排除以下敏感/无用内容：")
    logger.info(f"   目录: {', '.join(sorted(EXCLUDE_DIRS))}")
    logger.info(f"   文件: {', '.join(sorted(EXCLUDE_FILES))}")
    logger.info(f"   扩展: {', '.join(sorted(EXCLUDE_EXTENSIONS))}")

    return output_path


if __name__ == "__main__":
    pack_project()
