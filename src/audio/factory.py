import os
import sys
import subprocess
import shutil
import importlib.metadata

# === 基础路径 ===
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# === 引擎配置 ===
ENGINE_CONFIGS = {
    "CosyVoice": {
        "path": os.path.join(CURRENT_DIR, "cosyvoice"),
        "repo_url": "https://github.com/FunAudioLLM/CosyVoice.git",
        "req_file": os.path.join(CURRENT_DIR, "requirements_cosyvoice.txt"),
        "check_files": ["cosyvoice", "model_dir"], 
        
        "submodules": {
            "Matcha-TTS": {
                "path": os.path.join(CURRENT_DIR, "cosyvoice", "third_party", "Matcha-TTS"),
                "repo_url": "https://github.com/shivammehta25/Matcha-TTS.git",
                "check_files": ["matcha", "setup.py"]
            }
        },
        "tips": "⚠️ CosyVoice 需要加载预训练模型，请确保 'pretrained_models' 目录已有模型文件。"
    }
}

class AudioEngineFactory:

    @staticmethod
    def _run_pip(args, cwd=None):
        """执行 pip 命令 (带日志清洗)"""
        # 强制使用清华源，解决国内下载依赖慢/失败的问题
        base_cmd = [sys.executable, "-m", "pip", "install", "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"]
        
        # 这里的 args 主要是包名列表
        cmd = base_cmd + args
        
        try:
            process = subprocess.Popen(
                cmd, cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', errors='replace'
            )
            for line in process.stdout:
                # 过滤掉一些无用的日志，保持界面清爽
                if "Requirement already satisfied" not in line:
                    yield f"    [pip] {line.strip()}\n"
            process.wait()
        except Exception as e:
            yield f"❌ pip 执行出错: {e}\n"

    @staticmethod
    def _get_installed_packages_set():
        """获取当前环境包集合"""
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
        🚀【智能标准模式】(Smart Standard)
        1. 依然检查本地是否已存在包（为了快）。
        2. 对于缺失的包，使用标准 pip 安装（允许自动拉取子依赖）。
        3. 这样既解决了 ruamel 缺失的问题，又不会无脑重装 numpy/torch。
        """
        if not os.path.exists(req_file):
            yield f"⚠️ 未找到依赖文件: {req_file}，跳过。\n"
            return

        yield f"🔍 正在扫描依赖文件 ({os.path.basename(req_file)})...\n"
        
        installed_set = AudioEngineFactory._get_installed_packages_set()
        missing_packages = []
        skipped_count = 0

        # 读取并过滤
        with open(req_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                
                # 简单解析包名
                clean_line = line.split(';')[0].strip()
                pkg_base_name = clean_line.split("==")[0].split(">=")[0].split("<=")[0].split("<")[0].split(">")[0].split("~=")[0].split("[")[0].strip().lower()
                
                if not pkg_base_name: continue

                # 特殊保护：如果本地已经有 torch/numpy，绝对不要让 requirements.txt 里的版本覆盖它
                # 但其他库（如 hyperpyyaml）如果缺失，就允许 pip 自动处理它的子依赖
                if pkg_base_name in installed_set:
                    skipped_count += 1
                else:
                    missing_packages.append(line)

        if skipped_count > 0:
            yield f"   ✅ 已跳过 {skipped_count} 个已存在的库。\n"

        if missing_packages:
            yield f"   👉 发现 {len(missing_packages)} 个缺失的库，准备安装...\n"
            
            # 写入临时文件
            safe_req_path = req_file + ".install.tmp"
            with open(safe_req_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(missing_packages))
            
            try:
                # ⚠️ 关键修改：去掉了 --no-deps
                # 这样 pip 会自动把 ruamel.yaml 等子依赖装上
                yield "   ⏳ 正在下载并安装依赖 (使用清华源)...\n"
                for log in AudioEngineFactory._run_pip(["-r", safe_req_path], cwd=CURRENT_DIR):
                    yield log
            finally:
                if os.path.exists(safe_req_path): os.remove(safe_req_path)
        else:
            yield "   ✅ 所有依赖均已满足。\n"

    @staticmethod
    def _ensure_repo(path, url, check_files=None, depth=1):
        """检查仓库是否存在且完备"""
        if os.path.exists(path):
            is_valid = True
            if check_files:
                for f in check_files:
                    target_check = os.path.join(path, f)
                    if not os.path.exists(target_check):
                        is_valid = False
                        break
            
            if os.listdir(path) and is_valid:
                yield f"   ✅ 检测到目录完整: {os.path.basename(path)}，跳过下载。\n"
                return True
            else:
                yield f"   ⚠️ 目录不完整 ({os.path.basename(path)})，准备重置...\n"
                try:
                    shutil.rmtree(path)
                except Exception as e:
                    yield f"❌ 无法删除旧目录: {e}\n"
                    return False

        yield f"📦 正在克隆: {os.path.basename(path)}...\n"
        
        parent_dir = os.path.dirname(path)
        if not os.path.exists(parent_dir): 
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except Exception as e:
                yield f"❌ 创建目录失败: {parent_dir}, {e}\n"
                return False

        try:
            subprocess.run(["git", "clone", "--depth", str(depth), url, path], check=True)
            yield "   ✅ 克隆成功。\n"
            return True
        except subprocess.CalledProcessError as e:
            yield f"❌ Clone 失败: {e}\n"
            return False

    @staticmethod
    def manual_install_stream(engine_type):
        """安装主流程"""
        config = ENGINE_CONFIGS.get(engine_type)
        if not config:
            yield f"❌ 未找到配置: {engine_type}\n"
            return

        yield f"🚀 [System] 开始部署 {engine_type} ...\n"

        # 1. 主仓库
        for log in AudioEngineFactory._ensure_repo(config["path"], config["repo_url"], config.get("check_files")):
            yield log

        # 2. 子模块
        submodules = config.get("submodules", {})
        if submodules:
            yield "🔗 [Submodules] 检查子依赖仓库...\n"
            for sub_name, sub_conf in submodules.items():
                for log in AudioEngineFactory._ensure_repo(sub_conf["path"], sub_conf["repo_url"], sub_conf.get("check_files")):
                    yield log

        # 3. 依赖安装 (改为智能标准模式)
        yield "📦 [Dependencies] 检查依赖环境...\n"
        req_file = config.get("req_file")
        if req_file:
            # 使用新逻辑
            for log in AudioEngineFactory._install_smart_standard(req_file):
                yield log
        
        if config.get("tips"):
            yield f"\n{config['tips']}\n"

        yield f"\n🎉 {engine_type} 部署流程结束！\n"

    @staticmethod
    def remove_engine(engine_type):
        """卸载逻辑"""
        config = ENGINE_CONFIGS.get(engine_type)
        if not config: return "❌ 配置错误"

        deleted = []
        if os.path.exists(config["path"]):
            try:
                shutil.rmtree(config["path"])
                deleted.append(os.path.basename(config["path"]))
            except Exception as e:
                return f"❌ 删除主目录失败: {e}"
        
        submodules = config.get("submodules", {})
        for sub_name, sub_conf in submodules.items():
            if os.path.exists(sub_conf["path"]):
                try:
                    shutil.rmtree(sub_conf["path"])
                    deleted.append(sub_name)
                except:
                    pass

        if not deleted:
            return "⚠️ 目录不存在，无需卸载"
        return f"✅ 已卸载: {', '.join(deleted)}"

    @staticmethod
    def check_engine_status(engine_type):
        """检查状态"""
        config = ENGINE_CONFIGS.get(engine_type)
        if not config: return "❌ 配置错误"

        if not os.path.exists(config["path"]): return "❌ 源码未安装"
        
        submodules = config.get("submodules", {})
        for sub_name, sub_conf in submodules.items():
            if not os.path.exists(sub_conf["path"]): return f"⚠️ 缺少子模块: {sub_name}"

        model_check = os.path.join(config["path"], "pretrained_models")
        if os.path.exists(model_check) and not os.listdir(model_check):
             return "⚠️ 模型目录为空"
        
        return "✅ 引擎就绪"

    @staticmethod
    def get_engine_stream(engine_type, model_dir=None):
        """加载引擎"""
        config = ENGINE_CONFIGS.get(engine_type)
        if not config: 
            yield f"❌ 未知引擎: {engine_type}\n"; return

        paths_to_add = [config["path"]]
        submodules = config.get("submodules", {})
        for sub in submodules.values():
            paths_to_add.append(sub["path"])
            
        for p in paths_to_add:
            if p not in sys.path:
                sys.path.append(p)

        try:
            if engine_type == "CosyVoice":
                yield f"🚀 正在初始化 {engine_type} 内核...\n"
                try:
                    from .tts_engine import TTSEngine
                except ImportError as e:
                    yield f"❌ 错误: 无法导入 tts_engine.py: {e}\n"
                    yield None
                    return

                engine = TTSEngine(model_dir)
                
                if hasattr(engine, 'model') and engine.model is None:
                     yield "❌ 模型加载失败 (engine.model is None)\n"
                     yield None
                else:
                    yield f"✨ {engine_type} 加载成功！\n"
                    yield engine 
            else:
                yield f"⚠️ 暂不支持的引擎: {engine_type}\n"
                yield None

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"❌ 运行时崩溃: {e}\n"
            yield None