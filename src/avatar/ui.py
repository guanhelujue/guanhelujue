import gradio as gr
import os
import shutil

# 定义当前生效的头像路径
CURRENT_AVATAR_PATH = os.path.join("assets", "current_avatar.png")
DEFAULT_AVATAR = os.path.join("assets", "avatar", "default.png")

def save_avatar(image_path):
    """用户上传图片后，保存为系统当前的 '那张脸'"""
    if not image_path:
        return None
    
    # 复制并重命名，确保路径固定
    shutil.copy(image_path, CURRENT_AVATAR_PATH)
    return CURRENT_AVATAR_PATH

def get_current_avatar():
    if os.path.exists(CURRENT_AVATAR_PATH):
        return CURRENT_AVATAR_PATH
    if os.path.exists(DEFAULT_AVATAR):
        return DEFAULT_AVATAR
    return None

def build_avatar_ui():
    with gr.Column():
        gr.Markdown("### 📸 数字人形象设定 (Avatar Setup)")
        gr.Markdown("请上传一张**正脸、五官清晰**的图片。SadTalker 将驱动这张脸说话。")
        
        with gr.Row():
            # 上传区
            upload_component = gr.Image(
                label="上传新形象", 
                type="filepath",
                sources=["upload"]
            )
            
            # 预览区 (显示当前生效的脸)
            current_display = gr.Image(
                label="当前生效形象", 
                value=get_current_avatar(),
                interactive=False
            )

        save_btn = gr.Button("💾 确认为当前形象", variant="primary")
        
        # 事件
        save_btn.click(
            save_avatar,
            inputs=[upload_component],
            outputs=[current_display]
        )

    # 返回这个路径获取函数，供主程序调用
    return get_current_avatar