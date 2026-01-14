import os
import sys

# === 路径定义 ===
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG_DIR = os.path.join(CURRENT_DIR, "ffmpeg")

def ensure_ffmpeg_path():
    """
    【Windows 专用】运行时注入 FFmpeg 环境变量
    对应截图1中的 "Setup FFmpeg" 步骤
    """
    # 1. 寻找 bin 目录
    bin_path = os.path.join(FFMPEG_DIR, "bin")
    
    # 容错：如果解压后 ffmpeg.exe 直接在根目录
    if not os.path.exists(bin_path) and os.path.exists(FFMPEG_DIR):
        if os.path.exists(os.path.join(FFMPEG_DIR, "ffmpeg.exe")):
            bin_path = FFMPEG_DIR
    
    if os.path.exists(bin_path):
        # 注入 PATH (让系统能找到 ffmpeg 命令)
        os.environ["PATH"] = bin_path + ";" + os.environ.get("PATH", "")
        
        # [关键] 注入 MuseTalk 专用变量 (截图1最下方要求 export FFMPEG_PATH=...)
        ffmpeg_exe = os.path.join(bin_path, "ffmpeg.exe")
        if os.path.exists(ffmpeg_exe):
            os.environ["FFMPEG_PATH"] = ffmpeg_exe
            print(f"🔧 [Env] FFmpeg 路径已注入: {ffmpeg_exe}")
    else:
        pass