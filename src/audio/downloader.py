import os
import sys

# === 1. 定义模型映射表 ===
MODEL_MAP = {
    "CosyVoice-300M (推荐/标准版)": {
        "ms": "iic/CosyVoice-300M",
        "hf": "FunAudioLLM/CosyVoice-300M",
        "dir": "CosyVoice-300M",
        "engine": "CosyVoice" # 标记所属引擎
    },
    "CosyVoice-300M-SFT (微调版)": {
        "ms": "iic/CosyVoice-300M-SFT",
        "hf": "FunAudioLLM/CosyVoice-300M-SFT",
        "dir": "CosyVoice-300M-SFT",
        "engine": "CosyVoice"
    },
    "CosyVoice-300M-Instruct (指令版)": {
        "ms": "iic/CosyVoice-300M-Instruct",
        "hf": "FunAudioLLM/CosyVoice-300M-Instruct",
        "dir": "CosyVoice-300M-Instruct",
        "engine": "CosyVoice"
    },
    "CosyVoice2-0.5B (v2新版)": {
        "ms": "iic/CosyVoice2-0.5B",
        "hf": "FunAudioLLM/CosyVoice2-0.5B",
        "dir": "CosyVoice2-0.5B",
        "engine": "CosyVoice"
    },
    "CosyVoice-ttsfrd (资源文件)": {
        "ms": "iic/CosyVoice-ttsfrd",
        "hf": "FunAudioLLM/CosyVoice-ttsfrd",
        "dir": "CosyVoice-ttsfrd",
        "engine": "CosyVoice"
    }
}

def download_model_handler(source_type, model_key):
    """
    下载处理器 (生成器函数，用于实时返回日志)
    """
    if not model_key:
        yield "⚠️ 请先选择要下载的模型！"
        return

    model_info = MODEL_MAP.get(model_key)
    if not model_info:
        yield "❌ 未知的模型 Key"
        return

    # === 路径计算优化 ===
    # 目标结构: assets/models/{EngineName}/{ModelName}
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    
    # 1. 基础模型目录 assets/models
    base_models_dir = os.path.join(project_root, "assets", "models")
    
    # 2. 引擎专属目录 (例如 assets/models/CosyVoice)
    engine_sub_dir = model_info.get("engine", "Others") 
    final_parent_dir = os.path.join(base_models_dir, engine_sub_dir)
    
    # 3. 最终模型目录
    target_dir = os.path.join(final_parent_dir, model_info['dir'])

    repo_id = model_info["ms"] if source_type == "ModelScope (国内推荐)" else model_info["hf"]
    
    yield f"🚀 准备从 {source_type} 下载..."
    yield f"📦 模型 ID: {repo_id}"
    yield f"📂 存放路径: {target_dir}"
    yield "⏳ 正在初始化下载进程 (如果模型很大，请耐心等待控制台输出进度)..."

    try:
        if source_type == "ModelScope (国内推荐)":
            try:
                from modelscope import snapshot_download
            except ImportError:
                yield "❌ 缺少 modelscope 库。请在终端运行: pip install modelscope"
                return
            
            snapshot_download(repo_id, local_dir=target_dir)
            
        else: # HuggingFace
            try:
                from huggingface_hub import snapshot_download
            except ImportError:
                yield "❌ 缺少 huggingface_hub 库。请在终端运行: pip install huggingface_hub"
                return
            
            snapshot_download(repo_id, local_dir=target_dir)

        yield f"✅ 下载完成！\n📁 模型已保存在: {target_dir}\n🔄 请在 Step 2 点击刷新按钮加载新模型。"

    except Exception as e:
        yield f"❌ 下载失败: {str(e)}\n(请检查网络连接或磁盘空间)"