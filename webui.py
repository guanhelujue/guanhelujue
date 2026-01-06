import gradio as gr
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from configs.ui import build_config_ui
from src.audio.ui import build_audio_ui, get_tts
from src.brain.ui import build_brain_ui, user_input_handler, brain_think_handler
from src.avatar.ui import build_avatar_ui, get_current_avatar
from src.video.engine import get_sadtalker

# === 桥接函数 ===
def tts_bridge(text, ref_audio, ref_text):
    if not text or not ref_audio: return None
    tts = get_tts() 
    if not tts: return None
    output_path = os.path.join("assets", "reply.wav")
    return tts.speak(text, ref_audio, ref_text, output_file=output_path)

def video_bridge(audio_path):
    """
    连接 TTS 音频 -> SadTalker 视频
    """
    if not audio_path: return None
    
    # 获取当前头像
    source_image = get_current_avatar()
    if not source_image:
        print("⚠️ 未设置头像，无法生成视频")
        return None
        
    engine = get_sadtalker()
    # 生成视频
    video_path = engine.generate(source_image, audio_path)
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
                        chatbot, msg_input, submit_btn, clear_btn, _ = build_brain_ui()

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
                print("🎬 正在渲染 SadTalker 视频，这需要一点时间...")
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