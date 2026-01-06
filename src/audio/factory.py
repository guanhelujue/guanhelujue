import os
import sys
import subprocess
import shutil
import tempfile
from src.utils import check_package_installed, install_requirements_stream

# CURRENT_DIR 就是 E:\AI Project\test\src\audio
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPOS = {
    "CosyVoice": "https://github.com/FunAudioLLM/CosyVoice.git",
    "Matcha-TTS": "https://github.com/shivammehta25/Matcha-TTS.git"
}

class AudioEngineFactory:
    
    @staticmethod
    def _is_engine_installed(engine_name):
        if engine_name == "CosyVoice":
            path_core = os.path.join(CURRENT_DIR, "cosyvoice")
            path_matcha = os.path.join(CURRENT_DIR, "third_party", "Matcha-TTS")
            return os.path.exists(path_core) and os.path.exists(path_matcha)
        return False

    @staticmethod
    def _download_and_install_cosyvoice_stream():
        """
        【生成器】分步下载流程 (内部使用)
        """
        yield "📦 [Step 1/3] 检测 Git 环境...\n"
        try:
            subprocess.run(["git", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            yield "❌ 错误: 未安装 Git，无法下载源码。\n"
            yield False # 失败信号
            return

        with tempfile.TemporaryDirectory() as temp_dir:
            # === 1. CosyVoice ===
            yield f"📦 [Step 2/3] 正在下载 CosyVoice 核心源码...\n"
            yield f"   -> 来源: {REPOS['CosyVoice']}\n"
            
            try:
                cv_temp = os.path.join(temp_dir, "cv_repo")
                proc = subprocess.run(["git", "clone", "--depth", "1", REPOS["CosyVoice"], cv_temp], capture_output=True, text=True)
                if proc.returncode != 0:
                    yield f"❌ CosyVoice 下载失败:\n{proc.stderr}\n"
                    yield False
                    return
                
                yield "   -> 提取核心文件夹...\n"
                src_core = os.path.join(cv_temp, "cosyvoice")
                dst_core = os.path.join(CURRENT_DIR, "cosyvoice")
                if os.path.exists(dst_core): shutil.rmtree(dst_core)
                shutil.copytree(src_core, dst_core)
                yield "✅ CosyVoice 核心部署完成。\n"
                
            except Exception as e:
                yield f"❌ CosyVoice 部署异常: {e}\n"
                yield False
                return

            # === 2. Matcha-TTS ===
            yield f"📦 [Step 3/3] 正在下载 Matcha-TTS 依赖库...\n"
            yield f"   -> 来源: {REPOS['Matcha-TTS']}\n"
            
            try:
                matcha_temp = os.path.join(temp_dir, "matcha_repo")
                proc = subprocess.run(["git", "clone", "--depth", "1", REPOS["Matcha-TTS"], matcha_temp], capture_output=True, text=True)
                if proc.returncode != 0:
                    yield f"❌ Matcha-TTS 下载失败:\n{proc.stderr}\n"
                    yield False
                    return

                dst_matcha = os.path.join(CURRENT_DIR, "third_party", "Matcha-TTS")
                if not os.path.exists(os.path.dirname(dst_matcha)):
                    os.makedirs(os.path.dirname(dst_matcha), exist_ok=True)

                if os.path.exists(dst_matcha): shutil.rmtree(dst_matcha)
                shutil.copytree(matcha_temp, dst_matcha)
                yield "✅ Matcha-TTS 部署完成。\n"

            except Exception as e:
                yield f"❌ Matcha-TTS 部署异常: {e}\n"
                yield False
                return

        yield "🎉 所有源码组件部署成功！\n"
        yield True # 成功信号

    @staticmethod
    def manual_install_stream(engine_type):
        """
        【UI专用】手动安装流程接口
        """
        if engine_type == "CosyVoice":
            yield f"🚀 [System] 开始手动部署 {engine_type} 环境...\n"
            
            # 1. 下载源码
            success = False
            for log in AudioEngineFactory._download_and_install_cosyvoice_stream():
                if isinstance(log, bool): success = log
                else: yield log
            
            if not success:
                yield "❌ 源码部署失败，流程终止。\n"
                return

            # 2. 安装依赖
            # === 🛠️ 修复点：使用绝对路径 ===
            req_file = os.path.join(CURRENT_DIR, "requirements_cosyvoice.txt")
            
            yield f"📦 [Step 4] 检查并安装 Python 依赖 ({req_file})...\n"
            
            # 检查文件是否存在，不存在则提示
            if not os.path.exists(req_file):
                 yield f"❌ 错误：找不到依赖文件：{req_file}\n"
                 yield "   请确认 requirements_cosyvoice.txt 是否在 src/audio 目录下。\n"
                 return

            for log in install_requirements_stream(req_file):
                if not isinstance(log, bool): yield log

            yield f"\n🎉 {engine_type} 环境手动部署完成！\n"
        else:
            yield f"❌ 暂不支持手动安装此引擎: {engine_type}\n"

    @staticmethod
    def remove_engine(engine_type):
        if engine_type == "CosyVoice":
            targets = ["cosyvoice", "third_party"]
            removed = []
            for t in targets:
                path = os.path.join(CURRENT_DIR, t)
                if os.path.exists(path):
                    shutil.rmtree(path)
                    removed.append(t)
            if not removed: return "⚠️ 无需卸载 (文件不存在)"
            return f"✅ 已删除: {', '.join(removed)}"
        return "❌ 不支持卸载"

    @staticmethod
    def get_engine_stream(engine_type, model_dir):
        if engine_type == "CosyVoice":
            # === 阶段 1: 源码检查与下载 ===
            if not AudioEngineFactory._is_engine_installed("CosyVoice"):
                yield "🔍 环境缺失，开始自动下载组装...\n"
                success = False
                for log in AudioEngineFactory._download_and_install_cosyvoice_stream():
                    if isinstance(log, bool): success = log
                    else: yield log
                
                if not success:
                    yield "❌ 源码下载失败，终止加载。\n"; yield None; return

            # === 阶段 2: 依赖检查 ===
            # === 🛠️ 修复点：使用绝对路径 ===
            req_file = os.path.join(CURRENT_DIR, "requirements_cosyvoice.txt")
            
            if not check_package_installed("conformer"):
                yield "⚠️ 检测到缺少 Python 依赖，开始安装...\n"
                if not os.path.exists(req_file):
                    yield f"❌ 严重错误：找不到 {req_file}\n"; yield None; return

                success = False
                for log in install_requirements_stream(req_file):
                    if isinstance(log, bool): success = log
                    else: yield log
                
                if not success:
                    yield "❌ 依赖安装失败。\n"; yield None; return
            else:
                yield "✅ Python 依赖检查通过。\n"

            # === 阶段 3: 注入与加载 ===
            yield "🚀 正在初始化引擎内核...\n"
            paths = [
                os.path.join(CURRENT_DIR, "cosyvoice"),
                os.path.join(CURRENT_DIR, "third_party", "Matcha-TTS")
            ]
            for p in paths:
                if p not in sys.path: sys.path.append(p)

            try:
                from .tts_engine import TTSEngine
                engine = TTSEngine(model_dir)
                if engine.model:
                    yield "✨ 引擎加载成功！\n"
                    yield engine
                else:
                    yield "❌ 引擎初始化失败\n"; yield None
            except Exception as e:
                import traceback; traceback.print_exc()
                yield f"❌ 运行时崩溃: {e}\n"; yield None
        
        else:
            yield f"❌ 未知引擎: {engine_type}\n"; yield None