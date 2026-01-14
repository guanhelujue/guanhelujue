import os
import sys
import subprocess
import shutil
import zipfile
import urllib.request
import importlib.metadata 
import re

# === 基础路径 ===
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG_DIR = os.path.join(CURRENT_DIR, "ffmpeg")

# === Windows FFmpeg 源 ===
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

# === 引擎配置 ===
ENGINE_CONFIGS = {
    "SadTalker": {
        "path": os.path.join(CURRENT_DIR, "sadtalker"),
        "repo_url": "https://mirror.ghproxy.com/https://github.com/OpenTalker/SadTalker.git",
        "req_file": os.path.join(CURRENT_DIR, "requirements_sadtalker.txt"),
        "nodeps_packages": ["filterpy", "numba", "facexlib", "gfpgan", "basicsr"],
        "check_path": "checkpoints", 
        "use_mim": False
    },
    "MuseTalk": {
        "path": os.path.join(CURRENT_DIR, "musetalk"),
        "repo_url": "https://github.com/TMElyralab/MuseTalk.git",
        "req_file": os.path.join(CURRENT_DIR, "requirements_musetalk.txt"),
        "check_path": "models",
        "use_mim": True, 
        "mim_packages": ["mmengine", "mmcv==2.0.1", "mmdet==3.1.0", "mmpose==1.1.0"],
        "tips": "⚠️ MuseTalk 首次运行会自动编译 CUDA 算子，可能卡顿 5-10 分钟，请耐心等待。"
    }
}

class AvatarEngineFactory:

    @staticmethod
    def _create_lock_file(lock_path):
        """
        🛡️【核心锁】创建一个约束文件，锁定核心库版本。
        告诉 pip: "你可以安装依赖，但绝对不要升级这些库"
        """
        # 这些是绝对不能被升级的库，否则环境会崩
        critical_packages = ["numpy", "torch", "torchvision", "torchaudio", "gradio"]
        
        locks = []
        for pkg in critical_packages:
            try:
                # 获取当前环境已安装的版本
                ver = importlib.metadata.version(pkg)
                locks.append(f"{pkg}=={ver}")
            except:
                pass # 没装就不锁
        
        with open(lock_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(locks))
        
        return len(locks)

    @staticmethod
    def _run_pip(args, cwd=None, use_lock=True):
        """执行 pip 命令 (带日志清洗 + 清华源 + 版本锁)"""
        # 1. 基础命令：强制清华源
        base_cmd = [sys.executable, "-m", "pip", "install", "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"]
        
        # 2. 生成版本锁 (Constraints)
        lock_file = os.path.join(CURRENT_DIR, "version_lock.tmp")
        lock_arg = []
        
        if use_lock:
            AvatarEngineFactory._create_lock_file(lock_file)
            # -c 参数告诉 pip 遵守约束文件
            lock_arg = ["-c", lock_file]

        # 3. 组合命令
        cmd = base_cmd + args + lock_arg
        
        try:
            process = subprocess.Popen(
                cmd, cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', errors='replace'
            )
            for line in process.stdout:
                if "Requirement already satisfied" not in line:
                    yield f"     [pip] {line.strip()}\n"
            process.wait()
        except Exception as e:
            yield f"❌ pip 执行出错: {e}\n"
        finally:
            # 清理锁文件
            if os.path.exists(lock_file):
                try: os.remove(lock_file)
                except: pass

    @staticmethod
    def _run_mim(args, cwd=None):
        """执行 mim 命令"""
        cmd = [sys.executable, "-m", "mim"] + args
        try:
            process = subprocess.Popen(
                cmd, cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', errors='replace'
            )
            for line in process.stdout:
                 yield f"     [mim] {line.strip()}\n"
            process.wait()
        except Exception as e:
            yield f"❌ mim 执行出错: {e}\n"

    @staticmethod
    def _install_ffmpeg_windows():
        """自动下载 FFmpeg"""
        if os.path.exists(os.path.join(FFMPEG_DIR, "bin", "ffmpeg.exe")):
            yield "✅ 检测到 FFmpeg 已安装，跳过下载。\n"
            return
        
        yield f"🎬 [FFmpeg] 正在下载 Windows 版本...\n"
        temp_zip = os.path.join(CURRENT_DIR, "ffmpeg_temp.zip")
        try:
            urllib.request.urlretrieve(FFMPEG_URL, temp_zip)
            yield "    ✅ 下载完成，正在解压...\n"
            extract_temp = os.path.join(CURRENT_DIR, "ffmpeg_extract_temp")
            if os.path.exists(extract_temp): shutil.rmtree(extract_temp)
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(extract_temp)
            items = os.listdir(extract_temp)
            if not items: raise Exception("解压为空")
            root_folder = os.path.join(extract_temp, items[0])
            if os.path.exists(FFMPEG_DIR): shutil.rmtree(FFMPEG_DIR)
            shutil.move(root_folder, FFMPEG_DIR)
            yield f"    ✅ FFmpeg 已安装至: {FFMPEG_DIR}\n"
        except Exception as e:
            yield f"❌ FFmpeg 安装失败: {e}\n"
        finally:
            if os.path.exists(temp_zip): os.remove(temp_zip)
            if os.path.exists(extract_temp): shutil.rmtree(extract_temp)

    @staticmethod
    def _get_installed_packages_set():
        installed = set()
        try:
            for dist in importlib.metadata.distributions():
                installed.add(dist.metadata['Name'].lower())
        except Exception:
            try:
                result = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True)
                for line in result.stdout.splitlines():
                    if "==" in line:
                        installed.add(line.split("==")[0].lower())
            except:
                pass
        return installed

    @staticmethod
    def _install_smart_standard(req_file):
        """
        🚀【智能标准模式 + 锁定保护】
        1. 允许 pip 安装缺少的包及其依赖。
        2. 但是强制锁定 numpy/torch 版本，如果新包要求升级 numpy，pip 会尝试寻找旧版兼容包，或者报错（而不是默默破坏环境）。
        """
        if not os.path.exists(req_file):
            yield f"⚠️ 未找到依赖文件: {req_file}\n"
            return

        yield f"🔍 正在扫描依赖文件 ({os.path.basename(req_file)})...\n"
        
        installed_set = AvatarEngineFactory._get_installed_packages_set()
        missing_packages = []
        skipped_count = 0

        with open(req_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                clean_line = line.split(';')[0].strip()
                pkg_base_name = clean_line.split("==")[0].split(">=")[0].split("<=")[0].split("<")[0].split(">")[0].split("~=")[0].split("[")[0].strip().lower()
                
                if not pkg_base_name: continue
                if pkg_base_name in installed_set:
                    skipped_count += 1
                else:
                    missing_packages.append(line)

        if skipped_count > 0:
            yield f"   ✅ 已跳过 {skipped_count} 个已存在的库。\n"

        if missing_packages:
            yield f"   👉 发现 {len(missing_packages)} 个缺失库，安装并保护 Numpy/Torch...\n"
            
            safe_req_path = req_file + ".install.tmp"
            with open(safe_req_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(missing_packages))
            
            try:
                for log in AvatarEngineFactory._run_pip(["-r", safe_req_path], cwd=CURRENT_DIR, use_lock=True):
                    yield log
            finally:
                if os.path.exists(safe_req_path):
                    os.remove(safe_req_path)
        else:
            yield "   ✅ 所有依赖均已存在。\n"

    @staticmethod
    def manual_install_stream(engine_type):
        for log in AvatarEngineFactory._install_ffmpeg_windows():
            yield log

        config = ENGINE_CONFIGS.get(engine_type)
        if not config:
            yield f"❌ 未找到配置: {engine_type}\n"; return

        target_path = config["path"]
        yield f"🚀 [System] 开始部署 {engine_type} ...\n"

        # 1. Git Clone
        if not os.path.exists(target_path):
            yield f"📦 正在克隆源码...\n"
            try:
                subprocess.run(["git", "clone", "--depth", "1", config["repo_url"], target_path], check=True)
                yield "✅ 源码克隆成功。\n"
            except Exception as e:
                yield f"❌ Clone 失败: {e}\n"; return
        else:
            yield "ℹ️ 目录已存在，跳过克隆。\n"

        # 2. 依赖安装
        yield "📦 [Step 2] 安装依赖环境...\n"

        # 2.1 普通 Requirements (优先安装，带锁保护)
        req_file = config.get("req_file")
        if req_file:
            for log in AvatarEngineFactory._install_smart_standard(req_file):
                yield log
        
        # 2.2 无依赖包 (SadTalker等特殊依赖)
        nodeps = config.get("nodeps_packages", [])
        if nodeps:
            yield f"   👉 安装特殊依赖 (--no-deps)...\n"
            cmd = nodeps + ["--no-deps"]
            for log in AvatarEngineFactory._run_pip(cmd, cwd=CURRENT_DIR, use_lock=False):
                yield log

        # 2.3 MIM 组件 (后置安装)
        if config.get("use_mim"):
            yield "   👉 检查 OpenMIM...\n"
            installed_set = AvatarEngineFactory._get_installed_packages_set()
            
            # 必须先安装 openmim
            if "openmim" not in installed_set:
                yield "      + 安装 openmim 工具...\n"
                for log in AvatarEngineFactory._run_pip(["openmim"], cwd=CURRENT_DIR, use_lock=True):
                    yield log
            
            mim_pkgs = config.get("mim_packages", [])
            if mim_pkgs:
                yield f"   👉 安装 MIM 组件: {mim_pkgs} ...\n"
                install_cmd = ["install"] + mim_pkgs + ["--no-deps"]
                for log in AvatarEngineFactory._run_mim(install_cmd, cwd=CURRENT_DIR):
                    yield log

        if config.get("tips"): yield f"\n{config['tips']}\n"
        yield f"\n🎉 {engine_type} 部署流程结束！\n"

    @staticmethod
    def remove_engine(engine_type):
        config = ENGINE_CONFIGS.get(engine_type)
        if config and os.path.exists(config["path"]):
            try:
                shutil.rmtree(config["path"])
                return f"✅ 已卸载 {engine_type}"
            except Exception as e:
                return f"❌ 卸载失败: {e}"
        return "⚠️ 目录不存在"

    @staticmethod
    def check_engine_status(engine_type):
        config = ENGINE_CONFIGS.get(engine_type)
        if not config: return "❌ 配置错误"
        target_path = config["path"]
        if not os.path.exists(target_path): return "❌ 源码未安装"
        check_dir = config.get("check_path", "")
        if check_dir:
            full_check_path = os.path.join(target_path, check_dir)
            if not os.path.exists(full_check_path) or not os.listdir(full_check_path):
                return f"⚠️ 缺少模型文件"
        return "✅ 引擎就绪"