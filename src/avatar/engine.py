import os
import sys
import subprocess
import shutil
import uuid
import glob
import warnings
import yaml  # 必须引入 yaml 库 (pip install pyyaml)
from pydub import AudioSegment

# 忽略 diffusers 警告
warnings.filterwarnings("ignore", category=FutureWarning, module="diffusers")

# 引入环境管理器
from .env_manager import ensure_ffmpeg_path

# === 初始化时注入环境变量 ===
ensure_ffmpeg_path()

# === 路径 ===
current_dir = os.path.dirname(os.path.abspath(__file__))
sadtalker_path = os.path.join(current_dir, "sadtalker")
musetalk_path = os.path.join(current_dir, "musetalk")

class BaseEngine:
    def _preprocess_audio(self, input_audio):
        """降低音量，防止口型过大"""
        try:
            audio = AudioSegment.from_file(input_audio)
            quieter = audio - 10 
            temp_path = input_audio.replace(".wav", "_quiet.wav")
            quieter.export(temp_path, format="wav")
            return temp_path
        except:
            return input_audio

    def _get_safe_path(self, path, output_dir, prefix="t_"):
        """复制文件到纯英文路径"""
        if not os.path.exists(path): return path
        ext = os.path.splitext(path)[1]
        safe_name = f"{prefix}{uuid.uuid4().hex[:6]}{ext}"
        safe_path = os.path.abspath(os.path.join(output_dir, safe_name))
        try:
            shutil.copy(path, safe_path)
            return safe_path
        except:
            return path

    def _ensure_video_input(self, img_path, out_dir):
        """(MuseTalk专用) 如果是图片，转换为静态视频"""
        if not os.path.exists(out_dir): os.makedirs(out_dir, exist_ok=True)

        ext = os.path.splitext(img_path)[1].lower()
        # 只有图片才需要转换
        if ext in ['.jpg', '.jpeg', '.png', '.bmp']:
            safe_img = self._get_safe_path(img_path, out_dir, "tmp_cvt_")
            video_name = f"temp_v_{uuid.uuid4().hex[:4]}.mp4"
            video_path = os.path.abspath(os.path.join(out_dir, video_name))
            
            # 简单的 FFmpeg 转换命令
            cmd = [
                'ffmpeg', '-y', '-loop', '1', '-i', safe_img,
                '-c:v', 'libx264', '-t', '5', '-pix_fmt', 'yuv420p',
                '-vf', 'scale=512:512', video_path
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                return video_path
            except:
                return img_path # 失败返回原图
            finally:
                if os.path.exists(safe_img): os.remove(safe_img)
        
        return img_path

    def _find_video(self, root):
        files = glob.glob(os.path.join(root, "**", "*.mp4"), recursive=True)
        return max(files, key=os.path.getctime) if files else None

# ==========================================
# 1. SadTalker 引擎 (保持原样，使用命令行参数)
# ==========================================
class SadTalkerEngine(BaseEngine):
    def generate(self, img, audio, out_dir, **kwargs):
        script = os.path.join(sadtalker_path, "inference.py")
        
        safe_img = self._get_safe_path(img, out_dir, "src_")
        safe_audio = os.path.abspath(self._preprocess_audio(audio))
        
        # SadTalker 直接拼装命令行参数
        cmd = [
            sys.executable, script,
            "--driven_audio", safe_audio,
            "--source_image", safe_img,
            "--result_dir", out_dir,
            "--preprocess", "full"
        ]
        
        if kwargs.get("use_still"): cmd.append("--still")
        if kwargs.get("use_enhancer"): cmd += ["--enhancer", "gfpgan"]
        
        print(f"🎬 [SadTalker] 启动...")
        try:
            subprocess.run(cmd, check=True, cwd=sadtalker_path)
            return self._find_video(out_dir)
        except Exception as e:
            print(f"❌ SadTalker 失败: {e}")
            return None

# ==========================================
# 2. MuseTalk 引擎 (特殊处理：生成 YAML 配置)
# ==========================================
class MuseTalkEngine(BaseEngine):
    def generate(self, img, audio, out_dir, **kwargs):
        # 1. 确保输出目录存在，并获取绝对路径
        out_dir_abs = os.path.abspath(out_dir)
        if not os.path.exists(out_dir_abs):
            os.makedirs(out_dir_abs, exist_ok=True)

        # 2. 预处理：MuseTalk 不吃图片，先转视频
        # 注意：这里传给 _ensure_video_input 的要是绝对路径 out_dir_abs
        video_input = self._ensure_video_input(img, out_dir_abs)
        
        safe_video = self._get_safe_path(video_input, out_dir_abs, "src_mt_")
        safe_audio = os.path.abspath(audio) 
        
        # === 自动侦测模型配置路径 ===
        model_root = os.path.join(musetalk_path, "models", "musetalk")
        unet_config_path = None
        
        if os.path.exists(os.path.join(model_root, "musetalk.json")):
            unet_config_path = "models/musetalk/musetalk.json"
        elif os.path.exists(os.path.join(model_root, "config.json")):
            unet_config_path = "models/musetalk/config.json"
        
        if unet_config_path:
            print(f"✅ 检测到模型配置文件: {unet_config_path}")

        # 3. 构造 YAML 内容
        task_data = {
            "task_0": {
                "video_path": safe_video,
                "audio_path": safe_audio,
                "bbox_shift": kwargs.get("bbox_shift", 0)
            }
        }
        
        # 4. 写入临时 YAML 文件 (使用绝对路径)
        temp_yaml_name = f"temp_mt_config_{uuid.uuid4().hex[:4]}.yaml"
        # 【关键修改】这里必须用 os.path.abspath 确保是绝对路径
        temp_yaml_path = os.path.join(out_dir_abs, temp_yaml_name)
        
        try:
            with open(temp_yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(task_data, f)
        except Exception as e:
            print(f"❌ 无法写入配置文件: {e}")
            return None

        # 5. 启动命令
        cmd = [
            sys.executable, "-m", "scripts.inference",
            "--inference_config", temp_yaml_path, # 传绝对路径，怎么切目录都不怕
            "--result_dir", out_dir_abs           # 结果也输出到绝对路径
        ]
        
        if unet_config_path:
            cmd.extend(["--unet_config", unet_config_path])
        
        print(f"🎬 [MuseTalk] 启动 (配置路径: {temp_yaml_path})...")
        try:
            # cwd 依然保持在 musetalk 目录，以确保它能找到 models 文件夹
            subprocess.run(cmd, check=True, cwd=musetalk_path)
            return self._find_video(out_dir_abs)
        except Exception as e:
            print(f"❌ MuseTalk 失败: {e}")
            return None
        finally:
            # 调试阶段可以先注释掉这行，看看文件到底生成了没
            if os.path.exists(temp_yaml_path):
                os.remove(temp_yaml_path)

_engines = {}
def get_engine(name="SadTalker"):
    if not name: name = "SadTalker"
    if name not in _engines:
        if name == "SadTalker": _engines[name] = SadTalkerEngine()
        elif name == "MuseTalk": _engines[name] = MuseTalkEngine()
    return _engines.get(name)