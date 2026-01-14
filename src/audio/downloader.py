import os
import sys

# === 1. 定义模型映射表 ===
MODEL_MAP = {
    "CosyVoice-300M (推荐/标准版)": {
        "ms": "iic/CosyVoice-300M",
        "hf": "FunAudioLLM/CosyVoice-300M",
        "dir": "CosyVoice-300M",
        "engine": "CosyVoice"
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
    下载处理器 (修复版：修正路径计算)
    """
    if not model_key:
        yield "⚠️ 请先选择要下载的模型！"
        return

    model_info = MODEL_MAP.get(model_key)
    if not model_info:
        yield "❌ 未知的模型 Key"
        return

    # === 路径计算 (关键修复点) ===
    # 当前文件在 src/audio/downloader.py
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    if model_info["engine"] == "CosyVoice":
        # ✅ 修正：既然 current_dir 已经是 src/audio 了，就不要再拼 "audio" 了
        cosyvoice_root = os.path.join(current_dir, "cosyvoice")
        pretrained_root = os.path.join(cosyvoice_root, "pretrained_models")
        
        # 检查源码是否存在
        if not os.path.exists(cosyvoice_root):
             yield f"❌ 错误：未检测到 CosyVoice 源码目录。\n扫描路径: {cosyvoice_root}\n请先在【下载/修复引擎】中安装源码。"
             return
    else:
        # 回退逻辑 (assets/models)
        # src/audio -> src -> project_root
        project_root = os.path.dirname(os.path.dirname(current_dir))
        pretrained_root = os.path.join(project_root, "assets", "models", "Others")

    target_dir = os.path.join(pretrained_root, model_info['dir'])

    repo_id = model_info["ms"] if source_type == "ModelScope" else model_info["hf"]
    
    yield f"🚀 准备从 {source_type} 下载..."
    yield f"📦 模型 ID: {repo_id}"
    yield f"📂 存放路径: {target_dir}"
    
    # 自动创建父目录
    if not os.path.exists(pretrained_root):
        try:
            os.makedirs(pretrained_root, exist_ok=True)
        except:
            yield f"❌ 无法创建目录: {pretrained_root}"
            return

    yield "⏳ 正在初始化下载进程..."

    try:
        if source_type == "ModelScope":
            try:
                from modelscope import snapshot_download
            except ImportError:
                yield "❌ 缺少 modelscope 库。请先修复引擎环境。"
                return
            snapshot_download(repo_id, local_dir=target_dir)
            
        else: # HuggingFace
            try:
                from huggingface_hub import snapshot_download
            except ImportError:
                yield "❌ 缺少 huggingface_hub 库。请运行 pip install huggingface_hub"
                return
            snapshot_download(repo_id, local_dir=target_dir)

        yield f"✅ 下载完成！\n📁 模型已保存在源码目录中: {target_dir}"

    except Exception as e:
        yield f"❌ 下载失败: {str(e)}\n(请检查网络连接)"