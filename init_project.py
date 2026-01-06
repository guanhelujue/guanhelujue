import os

# 定义项目的目录结构
directories = [
    "src",
    "src/brain",
    "src/audio",
    "src/driver",
    "src/server",
    "assets/models",
    "assets/weights",
    "assets/logs",
    "docs",
    "tests",
    "configs",
    "scripts"
]

# 定义每个文件的内容
files_content = {
    # 1. 配置文件
    ".gitignore": "__pycache__/\n*.env\nassets/weights/\nassets/logs/\n.DS_Store\n",
    ".env": "OPENAI_API_KEY=your_key_here\nENV=development",
    ".env.example": "OPENAI_API_KEY=\nENV=development",
    "requirements.txt": "python-dotenv\ncolorama\n",
    
    # 2. 核心配置代码
    "configs/__init__.py": "",
    "configs/settings.py": """
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME = "GuanHeLuJue2 Digital Human"
    VERSION = "0.1.0"
    DEBUG = True

settings = Settings()
""",

    # 3. 大脑模块 (Brain)
    "src/__init__.py": "",
    "src/brain/__init__.py": "",
    "src/brain/llm_engine.py": """
import time

class LLMEngine:
    def __init__(self):
        print("[System] 大脑模块加载完毕...")

    def think(self, user_input):
        print(f"[Brain] 正在思考: {user_input} ...")
        time.sleep(1) # 模拟延迟
        return f"我听到了你说: {user_input}，这是来自 GuanHeLuJue2 的回复。"
""",

    # 4. 语音模块 (Audio)
    "src/audio/__init__.py": "",
    "src/audio/tts_engine.py": """
import time

class TTSEngine:
    def __init__(self):
        print("[System] 语音模块加载完毕...")

    def speak(self, text):
        print(f"[Audio] 正在合成语音: {text}")
        time.sleep(0.5)
        print("🔊 [播放]: " + text)
""",

    # 5. 主程序入口
    "main.py": """
import sys
import os
from colorama import init, Fore, Style

# 确保 src 目录在 python path 中
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from configs.settings import settings
from src.brain.llm_engine import LLMEngine
from src.audio.tts_engine import TTSEngine

init(autoreset=True)

class DigitalHumanApp:
    def __init__(self):
        print(Fore.CYAN + f"=== 启动项目: {settings.PROJECT_NAME} ===")
        self.brain = LLMEngine()
        self.audio = TTSEngine()
        print(Fore.GREEN + "=== 系统就绪，请输入对话 ===")

    def run(self):
        while True:
            try:
                user_input = input(Fore.YELLOW + "\\nUser: " + Style.RESET_ALL)
                if user_input.lower() in ['exit', 'quit']:
                    print("再见！")
                    break
                
                response = self.brain.think(user_input)
                print(Fore.MAGENTA + f"Bot: {response}")
                self.audio.speak(response)

            except KeyboardInterrupt:
                print("\\n程序退出")
                break

if __name__ == "__main__":
    app = DigitalHumanApp()
    app.run()
"""
}

def create_project_structure():
    base_path = os.getcwd()
    print(f"🚀 开始在 {base_path} 初始化项目...")

    # 创建目录
    for directory in directories:
        dir_path = os.path.join(base_path, directory)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print(f"✅ 创建目录: {directory}")

    # 创建文件
    for file_path, content in files_content.items():
        full_path = os.path.join(base_path, file_path)
        # 确保文件的父目录存在 (防止字典顺序问题)
        parent_dir = os.path.dirname(full_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content.strip())
        print(f"📄 创建文件: {file_path}")

    print("\n✨ 项目初始化完成！请运行 'python main.py' 启动。")

if __name__ == "__main__":
    create_project_structure()