import gradio as gr
import os
import json
from .factory import AvatarEngineFactory
from .downloader import MODEL_MAP, download_avatar_model_handler, MUSETALK_COMPONENTS

_current_config = {"engine": "SadTalker", "enhancer": True, "still": False, "bbox": 0, "img": None}
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "a2f_config.json")

def get_current_avatar():
    return _current_config["img"], _current_config

def install_handler(engine):
    log = ""
    for chunk in AvatarEngineFactory.manual_install_stream(engine):
        log += chunk
        yield log

def save_a2f_config(config):
    """将配置保存到 JSON 文件"""
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def load_a2f_config():
    """从文件读取配置，如果不存在则返回默认值"""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    # 默认值
    return {"engine": "SadTalker", "enhancer": True, "still": False, "bbox": 0, "img": None}

def check_musetalk_completeness(base_path):
    """
    检查 MuseTalk 所有模型文件是否下载完整
    base_path: src/avatar/musetalk 目录的绝对路径
    """
    missing_files = []
    
    for item in MUSETALK_COMPONENTS:
        # item["path"] 是相对路径，例如 "models/sd-vae/config.json"
        rel_path = item["path"]
        full_path = os.path.join(base_path, rel_path)
        
        # 检查文件是否存在且大小不为0
        if not os.path.exists(full_path):
            missing_files.append(rel_path)
            
    return missing_files

def load_handler(img, engine, enhancer, still, bbox):
    status = AvatarEngineFactory.check_engine_status(engine)
    if "❌" in status:
        yield f"流程终止: {status}", "❌ 引擎未就绪", None
        return
    
    if engine == "MuseTalk":
            current_dir = os.path.dirname(os.path.abspath(__file__))
            musetalk_root = os.path.join(current_dir, "musetalk")
            
            missing = check_musetalk_completeness(musetalk_root)
            if missing:
                log_str = "❌ MuseTalk 模型缺失，无法激活！\n请去【下载模型】页签重新下载以下文件：\n"
                for f in missing:
                    log_str += f" - {f}\n"
                yield log_str, "❌ 模型不全", None
                return

    if not img:
        yield "⚠️ 请上传图片", "❌ 无图片", None
        return

    _current_config.update({
        "engine": engine, "enhancer": enhancer, 
        "still": still, "bbox": bbox, "img": img
    })
    
    info = f"✅ 已激活形象: {os.path.basename(img)}\n"
    info += f"🚀 引擎: {engine}\n"
    if engine == "SadTalker":
        info += f"⚙️ 增强: {enhancer} | 静止: {still}"
    else:
        info += f"⚙️ 嘴型偏移: {bbox}"
    
    current_config = {
            "engine": engine, 
            "enhancer": enhancer, 
            "still": still, 
            "bbox": bbox, 
            "img": img
        }
    
    save_a2f_config(current_config)
    
    _current_config.update(current_config)

    yield info, "✅ 已激活", img



def build_avatar_ui():
    with gr.Column():
        # Step 1: 管理
        with gr.Group():
            gr.Markdown("### 1. 引擎管理")
            with gr.Tabs():
                with gr.Tab("🛠️ 安装"):
                    e_sel = gr.Dropdown(["SadTalker", "MuseTalk"], value="SadTalker", label="选择引擎")
                    i_btn = gr.Button("🚀 一键安装 (含 FFmpeg)", variant="primary")
                with gr.Tab("📥 下载模型"):
                    src = gr.Radio(["ModelScope", "HuggingFace"], value="ModelScope")
                    m_sel = gr.Dropdown(list(MODEL_MAP.keys()), value="SadTalker-V0.0.2 (核心模型)")
                    d_btn = gr.Button("☁️ 下载")
                with gr.Tab("🗑️ 卸载"):
                    u_sel = gr.Dropdown(["SadTalker", "MuseTalk"], value="SadTalker")
                    u_btn = gr.Button("⚠️ 卸载源码", variant="stop")

        # Step 2: 参数
        with gr.Group():
            gr.Markdown("### 2. 参数配置")
            eng_radio = gr.Radio(["SadTalker", "MuseTalk"], value="SadTalker", label="渲染核心")
            
            # SadTalker 面板
            with gr.Row(visible=True) as st_opt:
                use_enhancer = gr.Checkbox(True, label="面部增强")
                use_still = gr.Checkbox(False, label="静止模式")
            
            # MuseTalk 面板
            with gr.Row(visible=False) as mt_opt:
                bbox = gr.Slider(-10, 10, 0, step=1, label="嘴型偏移 (bbox_shift)")

        # Step 3: 激活
        with gr.Group():
            gr.Markdown("### 3. 形象激活")
            with gr.Row():
                inp = gr.Image(label="上传", type="filepath", height=250)
                out = gr.Image(label="预览", interactive=False, height=250)
            
            act_btn = gr.Button("💾 激活配置", variant="primary")
            log_box = gr.Textbox(label="日志", lines=3)
            stat_box = gr.Textbox(label="状态", interactive=False)

    # 事件绑定
    i_btn.click(install_handler, [e_sel], [log_box])
    d_btn.click(download_avatar_model_handler, [src, m_sel], [log_box])
    u_btn.click(lambda e: AvatarEngineFactory.remove_engine(e), [u_sel], [log_box])

    def toggle(e):
        return {st_opt: gr.update(visible=e=="SadTalker"), mt_opt: gr.update(visible=e=="MuseTalk")}
    eng_radio.change(toggle, [eng_radio], [st_opt, mt_opt])

    act_btn.click(load_handler, [inp, eng_radio, use_enhancer, use_still, bbox], [log_box, stat_box, out])