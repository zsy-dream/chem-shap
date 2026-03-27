import os
import sys
import webbrowser
import time
import socket
from threading import Thread
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 处理 PyInstaller 打包后的路径识别
def get_base_path():
    """获取程序运行时的静态资源根目录 (只读)"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的资源路径
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def get_data_path():
    """获取程序运行时的可写数据目录 (持久化)"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的可执行文件路径
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# 设置路径环境变量
BASE_DIR = get_base_path()      # 模板、静态资源等源文件路径
DATA_DIR = get_data_path()      # 数据库、上传、日志路径

# 将持久化路径存入环境变量，方便 app 初始化读取
os.environ['BASE_PATH'] = DATA_DIR 
sys.path.append(BASE_DIR)

from app import create_app, db
from tools.init_web_demo import init_database
from tools.create_demo_model import create_demo_model

HOST = '127.0.0.1'
PORT = 5001

def ensure_initialization():
    """确保数据库和演示模型已初始化"""
    db_path = os.path.join(DATA_DIR, 'instance', 'shap_medical_demo.db')
    if not os.path.exists(db_path):
        print("[INFO] 正在初始化数据库...")
        try:
            init_database()
            print("[INFO] 数据库初始化完成")
        except Exception as e:
            print(f"[ERROR] 数据库初始化失败: {e}")
    
    # 检查是否有模型
    model_dir = os.path.join(DATA_DIR, 'models')
    if not os.path.exists(model_dir) or not os.listdir(model_dir):
        print("[INFO] 正在创建演示模型...")
        try:
            create_demo_model()
            print("[INFO] 演示模型创建完成")
        except Exception as e:
            print(f"[ERROR] 演示模型创建失败: {e}")

def wait_for_server_and_open_browser():
    """等待服务器启动后打开浏览器"""
    url = f"http://{HOST}:{PORT}"
    # 最多等待 20 秒
    for _ in range(40):
        try:
            with socket.create_connection((HOST, PORT), timeout=0.5):
                print(f"[INFO] 服务器已就绪，正在打开浏览器: {url}")
                webbrowser.open(url)
                return
        except (OSError, ConnectionRefusedError):
            time.sleep(0.5)
    print("[WARN] 自动打开浏览器超时，请手动访问地址")

def main():
    print("="*60)
    print("  智析实验归因分析系统 - 启动中...")
    print("="*60)
    
    # 确保文件夹存在
    for folder in ['instance', 'models', 'uploads', 'logs']:
        os.makedirs(os.path.join(DATA_DIR, folder), exist_ok=True)
    
    # 打包运行无需自动初始化，通常建议在打包前就准备好
    # 但为了万无一失，这里还是尝试初始化
    ensure_initialization()
    app = create_app()
    
    # 启动浏览器线程
    Thread(target=wait_for_server_and_open_browser, daemon=True).start()
    
    print(f"\n[运行信息]")
    print(f"  地址: http://{HOST}:{PORT}")
    print(f"  用户: admin")
    print(f"  密码: admin123")
    print("-" * 30)
    
    # 运行 Flask
    app.run(host=HOST, port=PORT, debug=False)

if __name__ == "__main__":
    main()
