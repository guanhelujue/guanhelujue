import os
import sys
import subprocess
from pydub import AudioSegment  # 引入 pydub 处理音频

# === 路径注入 ===
current_dir = os.path.dirname(os.path.abspath(__file__))
sadtalker_path = os.path.join(current_dir, "sadtalker")

class SadTalkerEngine:
    def __init__(self):
        print("[Video] 初始化 SadTalker 引擎...")
        self.script_path = os.path.join(sadtalker_path, "inference.py")
        
    def _preprocess_audio(self, input_audio_path):
        """
        【关键优化】: 降低音频音量，防止嘴巴张太大
        """
        try:
            # 读取音频
            audio = AudioSegment.from_file(input_audio_path)
            
            # 降低 10 分贝 (这个数值可以调整，-6 到 -15 之间效果较好)
            # 声音越小，嘴巴动作幅度越小，越温柔
            quieter_audio = audio - 10 
            
            # 保存为临时文件
            temp_audio_path = input_audio_path.replace(".wav", "_quiet.wav")
            quieter_audio.export(temp_audio_path, format="wav")
            
            print(f"🔉 [Audio] 已自动降低音量 (-10dB) 以优化口型: {temp_audio_path}")
            return temp_audio_path
        except Exception as e:
            print(f"⚠️ 音频预处理失败 (请确保安装了 ffmpeg): {e}")
            # 如果失败，就用原声，虽然效果可能差点
            return input_audio_path

    def generate(self, source_image, driven_audio, output_dir="assets/video_out", use_still=False, use_enhancer=True):
        """
        生成视频
        :param use_still: 是否静止头部 (False=自然晃动, True=死板)
        :param use_enhancer: 是否开启面部增强 (True=清晰, False=模糊但快)
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        source_image = os.path.abspath(source_image)
        original_audio = os.path.abspath(driven_audio)
        output_dir = os.path.abspath(output_dir)

        # 1. 预处理音频 (降低音量)
        processed_audio = self._preprocess_audio(original_audio)
        processed_audio = os.path.abspath(processed_audio)

        # 2. 构造命令
        cmd = [
            sys.executable, 
            self.script_path,
            "--driven_audio", processed_audio,
            "--source_image", source_image,
            "--result_dir", output_dir,
            "--preprocess", "full"  # 如果你是动漫图且检测不到人脸，记得这里改成 'resize'
        ]

        # 【优化1】: 头部运动控制
        # 默认不加 --still，让头动起来；如果用户非要静止，才加
        if use_still:
            cmd.append("--still")
        
        # 【优化2】: 面部增强 (GFPGAN)
        # 开启后嘴唇会变清晰，减少"噪点式"抖动
        if use_enhancer:
            cmd.append("--enhancer")
            cmd.append("gfpgan")

        print(f"🎬 [Video] 启动渲染 | 头部运动: {'静止' if use_still else '自然'} | 增强: {'开启' if use_enhancer else '关闭'}")
        
        try:
            # cwd=sadtalker_path 保证能找到模型
            subprocess.run(cmd, check=True, cwd=sadtalker_path)
            
            # 渲染完清理临时音频
            if processed_audio != original_audio and os.path.exists(processed_audio):
                os.remove(processed_audio)

            return self._find_latest_video(output_dir)
            
        except subprocess.CalledProcessError as e:
            print(f"❌ 渲染进程崩溃: {e}")
            return None
        except Exception as e:
            print(f"❌ 未知错误: {e}")
            return None

    def _find_latest_video(self, root_dir):
        import glob
        search_pattern = os.path.join(root_dir, "**", "*.mp4")
        files = glob.glob(search_pattern, recursive=True)
        if not files: return None
        return max(files, key=os.path.getctime)

_video_engine = None
def get_sadtalker():
    global _video_engine
    if _video_engine is None:
        _video_engine = SadTalkerEngine()
    return _video_engine