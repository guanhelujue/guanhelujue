import gradio as gr
from .llm_engine import LLMEngine
import time

_brain_instance = None

def get_brain():
    global _brain_instance
    if _brain_instance is None:
        _brain_instance = LLMEngine()
    return _brain_instance

def build_brain_ui():
    with gr.Column():
        # 1. 聊天窗口
        chatbot = gr.Chatbot(
            height=500, 
            type="messages", 
            label="数字人交互",
            bubble_full_width=False
        )
        

        # 2. 输入区
        with gr.Row():
            msg_input = gr.Textbox(placeholder="请输入指令...", scale=9, autofocus=True)
            submit_btn = gr.Button("发送", variant="primary", scale=1)
        
        clear_btn = gr.Button("🗑️ 清空记忆")

    # 返回 audio_player 供主程序连线
    return chatbot, msg_input, submit_btn, clear_btn

# ... (user_input_handler 和 brain_think_handler 逻辑保持不变，不需要改) ...
# 为了完整性，这里列出 handler 的引用，实际代码请保留之前的逻辑
def user_input_handler(user_message, history):
    if not user_message: return "", history
    history.append({"role": "user", "content": user_message})
    return "", history

def brain_think_handler(history):
    brain = get_brain()
    history.append({"role": "assistant", "content": ""})
    if not brain:
        history[-1]['content'] = "❌ 大脑未连接"
        yield history, ""
        return
    
    try:
        user_text = history[-2]['content']
        generator = brain.think(user_text)
        if isinstance(generator, str): generator = [generator]
        
        full_response = ""
        for chunk in generator:
            full_response += chunk
            history[-1]['content'] = full_response
            yield history, full_response
            time.sleep(0.005)
    except Exception as e:
        history[-1]['content'] = f"Error: {e}"
        yield history, ""