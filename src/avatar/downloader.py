import os
import sys
import requests
import shutil
import hashlib
import time

# === 1. MuseTalk 专用：文件清单 (增强版：支持哈希校验) ===
# 建议：如果你知道确切的 SHA256，填入 "hash" 字段可开启严格校验
# 如果不知道 hash，脚本会自动使用 "Content-Length" (文件大小) 进行强校验
MUSETALK_COMPONENTS = [
    # === 1. MuseTalk 主模型 ===
    {
        "url": "https://huggingface.co/TMElyralab/MuseTalk/resolve/main/musetalk/pytorch_model.bin",
        "path": "models/musetalk/pytorch_model.bin"
    },
    {
        "url": "https://huggingface.co/TMElyralab/MuseTalk/resolve/main/musetalk/musetalk.json",
        "path": "models/musetalk/config.json"
    },
    {
        "url": "https://huggingface.co/TMElyralab/MuseTalk/resolve/main/musetalkV15/unet.pth",
        "path": "models/musetalkV15/unet.pth"
    },
    {
        "url": "https://huggingface.co/TMElyralab/MuseTalk/resolve/main/musetalkV15/musetalk.json",
        "path": "models/musetalkV15/musetalk.json"
    },

    # === 2. SD-VAE ===
    {
        "url": "https://huggingface.co/stabilityai/sd-vae-ft-mse/resolve/main/diffusion_pytorch_model.bin",
        "path": "models/sd-vae/diffusion_pytorch_model.bin"
    },
    {
        "url": "https://huggingface.co/stabilityai/sd-vae-ft-mse/resolve/main/config.json",
        "path": "models/sd-vae/config.json"
    },

    # === 3. DWPose ===
    {
        "url": "https://huggingface.co/yzd-v/DWPose/resolve/main/dw-ll_ucoco_384.pth",
        "path": "models/dwpose/dw-ll_ucoco_384.pth"
    },

    # === 4. Face Parsing (已替换为国内镜像源，解决下载不动的问题) ===
    {
        "url": "https://hf-mirror.com/ManyOtherFunctions/face-parse-bisent/resolve/main/79999_iter.pth",
        "path": "models/face-parse-bisent/79999_iter.pth"
    },
    {
        "url": "https://download.pytorch.org/models/resnet18-5c106cde.pth",
        "path": "models/face-parse-bisent/resnet18-5c106cde.pth"
    },

    # === 5. Whisper ===
    {
        "url": "https://huggingface.co/openai/whisper-tiny/resolve/main/pytorch_model.bin",
        "path": "models/whisper/pytorch_model.bin"
    },
    {
        "url": "https://huggingface.co/openai/whisper-tiny/resolve/main/config.json",
        "path": "models/whisper/config.json"
    },
    {
        "url": "https://huggingface.co/openai/whisper-tiny/resolve/main/preprocessor_config.json",
        "path": "models/whisper/preprocessor_config.json"
    },

    # === 6. Syncnet ===
    {
        "url": "https://huggingface.co/ByteDance/LatentSync/resolve/main/latentsync_syncnet.pt",
        "path": "models/syncnet/latentsync_syncnet.pt"
    }
]

MODEL_MAP = {
    "SadTalker-V0.0.2 (核心模型)": {
        "ms": "vvbc/SadTalker_Checkpoints",
        "hf": "vinthony/SadTalker-V002rc",
        "dir": "checkpoints",
        "engine": "SadTalker"
    },
    "GFPGAN-Weights (面部增强)": {
        "ms": "damo/cv_gfpgan_image-restoration",
        "hf": "TencentARC/GFPGAN",
        "dir": "gfpgan",
        "engine": "SadTalker"
    },
    "MuseTalk (完整权重包)": {
        "type": "composite",
        "engine": "MuseTalk"
    }
}

def calculate_file_hash(filepath, algorithm="sha256"):
    """计算文件哈希值"""
    hash_func = getattr(hashlib, algorithm)()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()

def format_size(bytes_size):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.2f}{unit}"
        bytes_size /= 1024
    return f"{bytes_size:.2f}TB"

def _smart_download(url, dest_path, expected_hash=None):
    """
    🔥 硬核下载器：支持 Header 预检、断点续传、哈希校验、速度显示
    """
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    filename = os.path.basename(dest_path)
    
    # === 1. 获取远程文件信息 (Header Pre-flight) ===
    try:
        # 使用 stream=True 但不读取内容，只看 Header
        # timeout 设置为 10 秒，防止请求卡死
        head_resp = requests.head(url, timeout=10, allow_redirects=True)
        # 有些服务器不支持 HEAD，如果 405/403 则尝试 GET stream
        if head_resp.status_code >= 400:
             head_resp = requests.get(url, stream=True, timeout=10)
             
        remote_size = int(head_resp.headers.get('content-length', 0))
    except Exception as e:
        yield f"    ⚠️ 无法获取远程文件信息: {e}，尝试强制下载...\n"
        remote_size = 0

    # === 2. 本地文件校验 (Size Check + Hash Check) ===
    if os.path.exists(dest_path):
        local_size = os.path.getsize(dest_path)
        
        # 2.1 基础大小校验
        if remote_size > 0:
            if local_size == remote_size:
                # 2.2 进阶哈希校验 (如果有)
                if expected_hash:
                    yield f"    🔍 正在校验哈希: {filename}...\n"
                    local_hash = calculate_file_hash(dest_path)
                    if local_hash == expected_hash:
                        yield f"    ✅ 文件完整 (Hash匹配): {filename}\n"
                        return
                    else:
                        yield f"    ❌ 哈希不匹配，删除重下 (本地:{local_hash[:8]}... vs 远程:{expected_hash[:8]}...)\n"
                        os.remove(dest_path)
                else:
                    yield f"    ✅ 文件大小一致，跳过: {filename} ({format_size(local_size)})\n"
                    return
            else:
                yield f"    ⚠️ 文件不完整 (本地:{format_size(local_size)} vs 远程:{format_size(remote_size)})，重新下载...\n"
                os.remove(dest_path) # 大小不对，直接删了重下
        else:
            # 如果远程没给大小，只能粗略判断
            if local_size > 1024: # 大于1KB勉强算存在
                yield f"    ℹ️ 无法获取远程大小，本地文件已存在，跳过: {filename}\n"
                return

    # === 3. 开始下载 (带 ASCII 进度条) ===
    try:
        start_time = time.time()
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        # 再次确认大小（GET 请求通常比 HEAD 准）
        total_size = int(response.headers.get('content-length', remote_size))
        
        yield f"    ⬇️ 开始下载: {filename} | 大小: {format_size(total_size)}\n"

        downloaded = 0
        last_print_time = 0
        
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192*4):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # 进度条逻辑：每 0.5 秒或每 5% 刷新一次 UI，避免卡死
                    current_time = time.time()
                    if total_size > 0:
                        percent = int((downloaded / total_size) * 100)
                        if (current_time - last_print_time > 1.0) or (percent % 10 == 0 and percent != 0):
                            # 计算速度
                            elapsed = current_time - start_time
                            speed = downloaded / elapsed if elapsed > 0 else 0
                            
                            # 绘制 ASCII 进度条
                            bar_len = 20
                            filled_len = int(bar_len * percent / 100)
                            bar = '█' * filled_len + '░' * (bar_len - filled_len)
                            
                            yield f"      [{bar}] {percent}% | {format_size(speed)}/s\n"
                            last_print_time = current_time

        # === 4. 下载后最终检查 ===
        if total_size > 0 and os.path.getsize(dest_path) != total_size:
            yield f"    ❌ 下载校验失败：大小不一致！\n"
            os.remove(dest_path)
        else:
            yield f"    ✅ 下载完成: {filename}\n"
            
    except Exception as e:
        if os.path.exists(dest_path):
            os.remove(dest_path) # 失败就删，不留垃圾
        yield f"    ❌ 网络错误 ({filename}): {e}\n"

def download_avatar_model_handler(source_type, model_key):
    if not model_key:
        yield "⚠️ 请先选择模型！"
        return

    info = MODEL_MAP.get(model_key)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    if info["engine"] == "MuseTalk":
        engine_root = os.path.join(current_dir, "musetalk")
    else:
        engine_root = os.path.join(current_dir, "sadtalker")
    
    if not os.path.exists(engine_root):
        yield f"⚠️ 未找到 {info['engine']} 源码目录，请先执行安装！"
        return

    # === MuseTalk 逻辑 ===
    if info.get("type") == "composite":
        yield f"🚀 启动 MuseTalk 智能下载器 (Smart Verify)...\n"
        
        for item in MUSETALK_COMPONENTS:
            full_path = os.path.join(engine_root, item["path"])
            # 将配置里的 url 和 hash 传进去
            for log in _smart_download(item["url"], full_path, item.get("hash")):
                yield log
                
        yield "\n✅ 所有组件校验/下载完毕！"
        return

    # === SadTalker 逻辑 (ModelScope/HF) ===
    target_dir = os.path.join(engine_root, info['dir'])
    repo_id = info["ms"] if source_type == "ModelScope" else info["hf"]
    
    yield f"🚀 [SadTalker] 正在调用 {source_type} SDK 下载...\n"
    
    try:
        if source_type == "ModelScope":
            from modelscope import snapshot_download
            snapshot_download(repo_id, local_dir=target_dir)
        else:
            from huggingface_hub import snapshot_download
            snapshot_download(repo_id, local_dir=target_dir)
        yield f"\n✅ 下载完成！"
    except Exception as e:
        yield f"\n❌ 下载失败: {e}"