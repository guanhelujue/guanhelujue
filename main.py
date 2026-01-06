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
                user_input = input(Fore.YELLOW + "\nUser: " + Style.RESET_ALL)
                if user_input.lower() in ['exit', 'quit']:
                    print("再见！")
                    break
                
                response = self.brain.think(user_input)
                print(Fore.MAGENTA + f"Bot: {response}")
                self.audio.speak(response)

            except KeyboardInterrupt:
                print("\n程序退出")
                break

if __name__ == "__main__":
    app = DigitalHumanApp()
    app.run()