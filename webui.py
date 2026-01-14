import matplotlib
matplotlib.use('Agg')
import gradio as gr
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from configs.ui import build_config_ui
from src.audio.ui import build_audio_ui, get_tts
from src.brain.ui import build_brain_ui, user_input_handler, brain_think_handler
from src.avatar.ui import build_avatar_ui, get_current_avatar, load_a2f_config
from src.avatar.engine import get_engine

# === 桥接函数 ===
def tts_bridge(text, ref_audio, ref_text):
    if not text or not ref_audio: return None
    tts = get_tts() 
    if not tts: return None
    output_path = os.path.join("assets", "reply.wav")
    return tts.speak(text, ref_audio, ref_text, output_file=output_path)

def video_bridge(audio_path):
    # 1. 直接从 JSON 文件读取最新的配置
    config = load_a2f_config()
    
    engine_name = config.get("engine", "SadTalker")
    img_path = config.get("img")

    if not img_path:
        raise ValueError("请先在'形象激活'面板上传图片并点击'激活配置'")

    # 2. 传入引擎名称，修复 TypeError
    engine = get_engine(engine_name)
    
    # 3. 根据不同引擎传入对应参数
    if engine_name == "SadTalker":
        video_path = engine.generate(
            img=img_path, 
            audio=audio_path, 
            out_dir="results",
            use_still=config.get("still", False),
            use_enhancer=config.get("enhancer", True)
        )
    elif engine_name == "MuseTalk":
        video_path = engine.generate(
            img=img_path, 
            audio=audio_path, 
            out_dir="results",
            bbox_shift=config.get("bbox", 0)
        )
    
    return video_path

def create_ui():
    with gr.Blocks(title="guanhelujue", theme=gr.themes.Soft()) as demo:
        with gr.Tabs():
            # Tab 1: Config
            with gr.TabItem("⚙️ 1. 系统配置"):
                build_config_ui()

            # Tab 2: Avatar (新增)
            with gr.TabItem("📸 2. 形象设定"):
                # 存文件系统（形象设定）
                build_avatar_ui()

            # Tab 3: TTS
            with gr.TabItem("🎙️ 3. 语音部署"):
                ref_audio, ref_text = build_audio_ui()

            # Tab 4: Chat (最终效果)
            with gr.TabItem("💬 4. 视频对话"):
                with gr.Row():
                    # 左侧：视频播放器
                    with gr.Column(scale=1):
                        video_display = gr.Video(
                            label="数字人实时演绎", 
                            autoplay=True,
                            height=500
                        )
                    
                    # 右侧：对话框
                    with gr.Column(scale=2):
                        chatbot, msg_input, submit_btn, clear_btn = build_brain_ui()

        # === 核心处理链 ===
        def processing_chain(history, ref_audio, ref_text):
            # 1. 思考 (流式出字)
            generator = brain_think_handler(history)
            final_text = ""
            for update_history, current_text in generator:
                final_text = current_text
                # 此时视频框不动
                yield update_history, None 
            
            # 2. 说话 (生成音频)
            audio_path = None
            if ref_audio and final_text:
                audio_path = tts_bridge(final_text, ref_audio, ref_text)
            
            # 3. 演戏 (生成视频)
            if audio_path:
                video_path = video_bridge(audio_path)
                if video_path:
                    # 播放视频
                    yield update_history, video_path
                else:
                    print("❌ 视频生成失败")
                    yield update_history, None

        # === 绑定 ===
        inputs_list = [chatbot, ref_audio, ref_text]
        outputs_list = [chatbot, video_display]

        submit_btn.click(
            user_input_handler, [msg_input, chatbot], [msg_input, chatbot]
        ).then(
            processing_chain, inputs_list, outputs_list
        )

        msg_input.submit(
            user_input_handler, [msg_input, chatbot], [msg_input, chatbot]
        ).then(
            processing_chain, inputs_list, outputs_list
        )
        
        clear_btn.click(lambda: [], None, chatbot)

    return demo

if __name__ == "__main__":
    ui = create_ui()
    ui.queue()
    ui.launch(inbrowser=True, server_name="127.0.0.1", server_port=7860)