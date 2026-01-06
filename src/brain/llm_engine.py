import os
from dotenv import load_dotenv

load_dotenv()

class LLMEngine:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "openai")
        self.api_key = os.getenv("LLM_API_KEY")
        self.base_url = os.getenv("LLM_BASE_URL")
        self.model_name = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        self.persona = os.getenv("DIGITAL_HUMAN_PERSONA", "你是一个数字人。")
        
        if not self.api_key:
            raise ValueError("❌ 未配置 API Key")

        # === 记忆初始化 ===
        # OpenAI/DeepSeek 使用列表维护记忆
        self.openai_history = [{"role": "system", "content": self.persona}]
        
        # Google Gemini 使用 ChatSession 对象维护记忆
        self.gemini_chat = None 

        print(f"[Brain] 初始化: {self.provider} / {self.model_name}")

        # === 客户端初始化 ===
        if self.provider == "google":
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model_name)
            # 启动 Gemini 的聊天模式 (它会自动管理 history)
            self.gemini_chat = self.client.start_chat(history=[
                {"role": "user", "parts": [f"System Prompt: {self.persona}"]},
                {"role": "model", "parts": ["OK, I understand my persona."]}
            ])
        else:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def think(self, user_input: str) -> str:
        print(f"[Brain] 思考中 ({self.provider}): {user_input}")

        try:
            # === 分支 A: Google Gemini (有上下文) ===
            if self.provider == "google":
                # 直接发送消息，Gemini 对象内部会自动 append history
                response = self.gemini_chat.send_message(user_input)
                return response.text

            # === 分支 B: OpenAI / DeepSeek (有上下文) ===
            else:
                # 1. 手动把用户的话加入历史列表
                self.openai_history.append({"role": "user", "content": user_input})
                
                # 2. 发送整个列表
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=self.openai_history, # <--- 关键：这里传的是整个历史
                    temperature=0.7,
                    max_tokens=200
                )
                reply_text = response.choices[0].message.content.strip()

                # 3. 手动把 AI 的话加入历史列表
                self.openai_history.append({"role": "assistant", "content": reply_text})
                
                return reply_text

        except Exception as e:
            error_msg = f"大脑短路: {str(e)}"
            print(error_msg)
            return error_msg