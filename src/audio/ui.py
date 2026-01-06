import gradio as gr
import os
import shutil
import re
from .factory import AudioEngineFactory
from src.utils import load_tts_settings, save_tts_settings
from .downloader import MODEL_MAP, download_model_handler

# 全局变量
_tts_instance = None
# 占位符
PLACEHOLDER_TEXT = "暂无模型-请先下载"

def get_tts():
    """获取当前已加载的 TTS 引擎实例"""
    global _tts_instance
    return _tts_instance

# ==========================================
# 1. 路径与扫描逻辑
# ==========================================

def get_models_root(engine_type):
    base = os.path.join("assets", "models")
    if engine_type == "CosyVoice":
        specific_dir = os.path.join(base, "CosyVoice")
        return specific_dir if os.path.exists(specific_dir) else base
    elif engine_type == "GPT-SoVITS":
        return os.path.join(base, "GPT-SoVITS")
    return base

def scan_models(engine_type):
    if engine_type == "GPT-SoVITS": 
        return ["GPT-SoVITS-暂未支持"]
        
    root = get_models_root(engine_type)
    if not os.path.exists(root): 
        try:
            os.makedirs(root, exist_ok=True)
        except Exception:
            pass
    
    if os.path.exists(root):
        dirs = [d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))]
    else:
        dirs = []
    
    if not dirs:
        return [PLACEHOLDER_TEXT]
    
    return dirs

def get_full_model_path(engine_type, model_name):
    root = get_models_root(engine_type)
    return os.path.abspath(os.path.join(root, model_name))

# ==========================================
# 2. 各种 Handler
# ==========================================

def on_engine_change(engine_type):
    new_choices = scan_models(engine_type)
    val = new_choices[0]
    is_interactive = (engine_type != "GPT-SoVITS")
    return gr.Dropdown(choices=new_choices, value=val, interactive=is_interactive, allow_custom_value=True)

def manual_install_handler(engine_type):
    if engine_type == "GPT-SoVITS":
        yield "⚠️ GPT-SoVITS 暂未开放自动安装。", "未执行"
        return

    log_buffer = f"🚀 [System] 开始部署 {engine_type} 源码...\n"
    yield log_buffer, "⏳ 初始化..."
    
    try:
        if hasattr(AudioEngineFactory, 'manual_install_stream'):
            for item in AudioEngineFactory.manual_install_stream(engine_type):
                if isinstance(item, str):
                    log_buffer += item
                    yield log_buffer, "⏳ 安装中..."
        else:
            yield log_buffer + "❌ 工厂类未实现接口", "❌ 错误"
            return
    except Exception as e:
        yield log_buffer + f"\n❌ 异常: {e}", "❌ 错误"
        return
    
    log_buffer += "\n✅ 操作结束。"
    yield log_buffer, "✅ 完成"

def delete_model_handler(engine_type, model_name):
    if not model_name or model_name == PLACEHOLDER_TEXT:
        return "⚠️ 无法删除占位符或无效模型"

    full_path = get_full_model_path(engine_type, model_name)
    if not os.path.exists(full_path): return f"❌ 路径不存在: {full_path}"
    try:
        shutil.rmtree(full_path)
        return f"✅ 已删除模型: {model_name}\n(路径: {full_path})"
    except Exception as e:
        return f"❌ 删除失败: {e}"

def uninstall_engine_handler(engine_name):
    if not engine_name: return "请选择引擎"
    return AudioEngineFactory.remove_engine(engine_name)

def load_and_save_stream_handler(engine_type, model_name, ref_audio, ref_text):
    global _tts_instance
    if engine_type == "GPT-SoVITS":
        yield "⚠️ 暂未支持 GPT-SoVITS", "暂不可用"
        return

    if not model_name or model_name == PLACEHOLDER_TEXT:
        yield "⚠️ 请先在 Step 1 下载模型，然后在 Step 2 刷新列表。", "等待操作..."
        return

    full_path = get_full_model_path(engine_type, model_name)
    
    if ref_audio and not os.path.isfile(ref_audio):
        ref_audio = "" 

    save_msg = save_tts_settings(engine_type, model_name, ref_audio, ref_text)
    
    log_content = f"--- 开始加载流程 ---\n{save_msg}\n引擎: {engine_type}\n模型: {model_name}\n"
    yield log_content, "⏳ 准备中..."

    try:
        generator = AudioEngineFactory.get_engine_stream(engine_type, full_path)
        for item in generator:
            if isinstance(item, str):
                log_content += item
                yield log_content, "⏳ 处理中..."
            elif item is None:
                # === 🛠️ 修复点：之前这里写成了逗号分隔，导致变成了 Tuple ===
                log_content += "\n❌ 加载失败，请检查日志。"
                yield log_content, "❌ 失败"
            else:
                _tts_instance = item
                log_content += "\n🎉 引擎加载成功！"
                yield log_content, "✅ 就绪"
    except Exception as e:
        # === 🛡️ 错误捕获 ===
        import traceback
        traceback.print_exc()
        log_content += f"\n❌ 崩溃: {str(e)}"
        yield log_content, "❌ 崩溃"

def auto_extract_text_from_filename(audio_path):
    if not audio_path or not os.path.isfile(audio_path): return ""
    try:
        filename = os.path.basename(audio_path)
        return re.sub(r"【.*?】|\[.*?\]", "", os.path.splitext(filename)[0]).strip()
    except: return ""

# ==========================================
# 3. UI 构建主函数
# ==========================================

def build_audio_ui():
    config = load_tts_settings()
    last_engine = config.get("engine_type", "CosyVoice")
    last_model_name = config.get("model_path", "")
    
    initial_choices = scan_models(last_engine)
    
    if initial_choices == [PLACEHOLDER_TEXT]:
        default_model_value = initial_choices[0]
    else:
        default_model_value = last_model_name if last_model_name in initial_choices else initial_choices[0]

    raw_audio_path = config.get("ref_audio")
    if raw_audio_path and os.path.isfile(raw_audio_path):
        default_audio = raw_audio_path
    else:
        default_audio = None 

    with gr.Column():
        gr.Markdown("### 🎙️ 语音合成 (TTS) 部署面板")
        
        with gr.Group():
            gr.Markdown("#### Step 1: 插件与资产管理 (Management)")
            with gr.Tabs():
                with gr.Tab("🛠️ 下载/修复引擎"):
                    gr.Markdown("第一次使用或环境损坏时，请先安装引擎核心代码。")
                    with gr.Row():
                        install_engine_select = gr.Dropdown(
                            choices=["CosyVoice", "GPT-SoVITS"], 
                            value="CosyVoice", 
                            label="选择要安装的引擎",
                            allow_custom_value=True
                        )
                        install_btn = gr.Button("🚀 执行安装/修复", variant="primary")
                
                with gr.Tab("📥 下载模型权重"):
                    gr.Markdown("有了源码还需要模型文件 (如 300M 版本)。")
                    with gr.Row():
                        source_radio = gr.Radio(["ModelScope", "HuggingFace"], value="ModelScope", label="下载源")
                        dl_model_select = gr.Dropdown(
                            list(MODEL_MAP.keys()), 
                            label="选择模型版本", 
                            value="CosyVoice-300M (推荐/标准版)",
                            allow_custom_value=True
                        )
                    dl_btn = gr.Button("☁️ 开始下载")

                with gr.Tab("🗑️ 卸载/清理"):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("##### 卸载源码")
                            uninstall_target = gr.Dropdown(["CosyVoice"], value="CosyVoice", label="目标引擎")
                            uninstall_eng_btn = gr.Button("⚠️ 卸载源码文件", variant="stop")
                        
                        with gr.Column():
                            gr.Markdown("##### 删除模型")
                            del_model_dropdown = gr.Dropdown(
                                initial_choices, 
                                label="选择要删除的模型", 
                                value=default_model_value, 
                                interactive=True,
                                allow_custom_value=True
                            )
                            with gr.Row():
                                refresh_del_btn = gr.Button("🔄 刷新", scale=1)
                                del_model_btn = gr.Button("🗑️ 确认删除", variant="stop", scale=2)

        gr.Markdown("---")

        with gr.Group():
            gr.Markdown("#### Step 2: 选择内核与模型 (Selection)")
            engine_radio = gr.Radio(choices=["CosyVoice", "GPT-SoVITS"], value=last_engine, label="选择 TTS 内核")
            with gr.Row():
                model_dropdown = gr.Dropdown(
                    choices=initial_choices, 
                    value=default_model_value, 
                    label="选择模型 (已下载)", 
                    interactive=True, 
                    scale=4,
                    allow_custom_value=True
                )
                refresh_main_btn = gr.Button("🔄 刷新", scale=1)

        gr.Markdown("---")

        with gr.Group():
            gr.Markdown("#### Step 3: 声音克隆素材 (Reference)")
            ref_audio_input = gr.Audio(label="参考音频 (3-10秒最佳)", type="filepath", value=default_audio)
            ref_text_input = gr.Textbox(label="参考文本", value=config.get("ref_text"), placeholder="留空则自动识别...")

        gr.Markdown("---")

        with gr.Group():
            gr.Markdown("#### Step 4: 启动引擎 (Launch)")
            with gr.Row():
                load_btn = gr.Button("💾 保存配置并加载引擎", variant="primary", scale=1)
                status_output = gr.Textbox(label="当前状态", value="等待加载...", interactive=False, scale=1)
            
            console_log = gr.Textbox(
                label="📟 系统运行日志 (Global Console)", 
                lines=10, 
                interactive=False,
                elem_classes=["console-log"],
                value="[System] 就绪。请在上方进行操作..."
            )

    # 绑定
    install_btn.click(manual_install_handler, inputs=[install_engine_select], outputs=[console_log, status_output])
    dl_btn.click(download_model_handler, inputs=[source_radio, dl_model_select], outputs=[console_log])
    uninstall_eng_btn.click(uninstall_engine_handler, inputs=[uninstall_target], outputs=[console_log])
    
    refresh_del_btn.click(
        lambda: gr.Dropdown(choices=scan_models(last_engine), allow_custom_value=True), 
        outputs=[del_model_dropdown]
    )
    
    del_model_btn.click(
        delete_model_handler, 
        inputs=[engine_radio, del_model_dropdown], 
        outputs=[console_log]
    ).then(
        on_engine_change, inputs=[engine_radio], outputs=[model_dropdown] 
    ).then(
        lambda: gr.Dropdown(choices=scan_models(last_engine), allow_custom_value=True), 
        outputs=[del_model_dropdown]
    )

    engine_radio.change(on_engine_change, inputs=[engine_radio], outputs=[model_dropdown])
    engine_radio.change(on_engine_change, inputs=[engine_radio], outputs=[del_model_dropdown]) 
    refresh_main_btn.click(on_engine_change, inputs=[engine_radio], outputs=[model_dropdown])
    ref_audio_input.change(auto_extract_text_from_filename, inputs=[ref_audio_input], outputs=[ref_text_input])

    load_btn.click(
        load_and_save_stream_handler,
        inputs=[engine_radio, model_dropdown, ref_audio_input, ref_text_input],
        outputs=[console_log, status_output]
    )

    return ref_audio_input, ref_text_input