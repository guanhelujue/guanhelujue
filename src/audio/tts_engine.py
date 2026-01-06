import os
import sys
import torch
import torchaudio

# === 路径注入 ===
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

matcha_path = os.path.join(current_dir, "third_party", "Matcha-TTS")
if os.path.exists(matcha_path) and matcha_path not in sys.path:
    sys.path.append(matcha_path)

try:
    from cosyvoice.cli.cosyvoice import CosyVoice
except ImportError as e:
    # 这里的 import 才是合法的，因为它引用的是外部库，而不是自己
    raise e

class TTSEngine:
    def __init__(self, model_dir):
        """
        初始化引擎
        :param model_dir: 模型文件夹的绝对路径
        """
        print(f"[Audio] 初始化 CosyVoice 引擎...")
        print(f"       目标模型: {model_dir}")

        if not model_dir or not os.path.exists(model_dir):
            print(f"❌ 找不到模型文件夹: {model_dir}")
            self.model = None
            return

        try:
            # 加载用户指定的模型
            self.model = CosyVoice(model_dir)
            print("✅ CosyVoice 内核加载成功！")
        except Exception as e:
            print(f"❌ 初始化崩溃: {e}")
            self.model = None

    def speak(self, text: str, reference_wav: str, prompt_text: str, output_file: str = "output.wav"):
        if not self.model:
            print("⚠️ 引擎未加载，请先选择模型并加载")
            return None

        if not reference_wav or not os.path.exists(reference_wav):
            print("⚠️ 参考音频路径无效")
            return None

        if not prompt_text: prompt_text = ""

        print(f"[Audio] 推理中: '{text}'")
        try:
            # 兼容性写法: 直接传路径字符串
            output = self.model.inference_zero_shot(text, prompt_text, reference_wav)
            
            for result in output:
                # 兼容性写法: 不传 backend 参数
                torchaudio.save(output_file, result['tts_speech'], 22050)
                print(f"🔊 生成成功 -> {output_file}")
                return output_file
                
        except Exception as e:
            print(f"❌ 推理出错: {e}")
            import traceback
            traceback.print_exc()
            return None

# 这里不需要 if __name__ == "__main__" 测试代码，因为外部调用逻辑变了