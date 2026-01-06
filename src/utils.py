import os
import json
from dotenv import load_dotenv
import re
import importlib
import sys
import tempfile
import subprocess

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')


def parse_emotion(text):
    """
    从文本中提取情绪标签，例如 "(开心)你好" -> 提取出 "happy"
    返回: (clean_text, emotion_key)
    """
    # 定义情绪映射表 (你可以根据需要添加更多)
    emotion_map = {
        "开心": "happy", "高兴": "happy", "笑": "happy", "哈哈": "happy",
        "生气": "angry", "愤怒": "angry", "哼": "angry",
        "难过": "sad", "伤心": "sad", "呜呜": "sad",
        "惊讶": "surprise", "震惊": "surprise",
        "普通": "default", "平静": "default"
    }
    
    # 1. 尝试用正则提取圆括号内容，如 (开心) 或 [生气]
    match = re.search(r"[\(\[\{](.*?)[\)\]\}]", text)
    emotion = "default"
    
    if match:
        tag = match.group(1)
        # 查找映射表
        for key, value in emotion_map.items():
            if key in tag:
                emotion = value
                break
        
        # 2. 从文本中移除标签，避免 TTS 把 "(开心)" 读出来
        clean_text = re.sub(r"[\(\[\{].*?[\)\]\}]", "", text)
    else:
        clean_text = text
    
    return clean_text.strip(), emotion

# ==========================================
# 1. 环境配置模块
# ==========================================

def load_settings():
    """加载api_key与数字人人设"""
    load_dotenv(ENV_PATH, override=True)
    return {
        # 新增 provider 字段，默认为 openai
        "provider": os.getenv("LLM_PROVIDER", "openai"),
        "api_key": os.getenv("LLM_API_KEY", ""),
        "base_url": os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
        "model": os.getenv("LLM_MODEL", "deepseek-chat"),
        "persona": os.getenv("DIGITAL_HUMAN_PERSONA", "你是一个数字人助手。")
    }

def save_settings(provider, api_key, base_url, model, persona):
    """保存环境配置"""
    os.environ["LLM_PROVIDER"] = provider
    os.environ["LLM_API_KEY"] = api_key
    os.environ["LLM_BASE_URL"] = base_url
    os.environ["LLM_MODEL"] = model
    os.environ["DIGITAL_HUMAN_PERSONA"] = persona
    
    lines = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()

    new_config = {
        "LLM_PROVIDER": provider,
        "LLM_API_KEY": api_key,
        "LLM_BASE_URL": base_url,
        "LLM_MODEL": model,
        "DIGITAL_HUMAN_PERSONA": persona
    }

    updated_lines = []
    processed_keys = set()

    for line in lines:
        key = line.split("=")[0].strip()
        if key in new_config:
            updated_lines.append(f"{key}={new_config[key]}\n")
            processed_keys.add(key)
        else:
            updated_lines.append(line)
    
    for key, value in new_config.items():
        if key not in processed_keys:
            updated_lines.append(f"\n{key}={value}\n")

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(updated_lines)
    
    return "✅ 配置已保存！"

# ==========================================
# 2. TTS 配置模块
# ==========================================
TTS_CONFIG_FILE = "tts_config.json"

def load_tts_settings():
    """加载TTS配置"""
    if not os.path.exists(TTS_CONFIG_FILE):
        return {
            "model_path": None,
            "ref_audio": None,
            "ref_text": None
        }
    try:
        with open(TTS_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_tts_settings(engine_type, model_name, ref_audio, ref_text=""):
    """
    保存 TTS 配置
    """
    try:
        config = load_tts_settings()
        config["engine_type"] = engine_type
        config["model_path"] = model_name
        
        # 路径清洗
        if ref_audio and os.path.isfile(ref_audio):
            config["ref_audio"] = ref_audio
        else:
            config["ref_audio"] = ""

        config["ref_text"] = ref_text
        
        with open(TTS_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
            
        return "✅ 配置已保存"
    except Exception as e:
        return f"❌ 保存失败: {e}"

# ==========================================
# 3. 依赖管理模块
# ==========================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 核心“宪法”文件：定义了绝对不能动的环境版本
MAIN_REQUIREMENTS_FILE = os.path.join(PROJECT_ROOT, "requirements.txt")
def check_package_installed(package_name):
    if package_name in sys.modules: return True
    try:
        spec = importlib.util.find_spec(package_name)
        return spec is not None
    except: return False

def _create_constraints_from_file():
    """
    【核心防御逻辑】
    读取根目录的 requirements.txt，提取所有包的版本号，生成一个临时的约束文件。
    任何新安装的包，都必须满足这里面的版本要求，否则报错。
    """
    if not os.path.exists(MAIN_REQUIREMENTS_FILE):
        print(f"⚠️ [警告] 未找到主依赖文件: {MAIN_REQUIREMENTS_FILE}，无法启用保护机制！")
        return None

    valid_constraints = []
    print(f"🛡️ [System] 正在读取主依赖锁: {MAIN_REQUIREMENTS_FILE}")
    
    try:
        with open(MAIN_REQUIREMENTS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 1. 跳过空行和注释
                if not line or line.startswith('#'):
                    continue
                # 2. 跳过 [source] 标记 (如果有)
                if line.startswith('[source'):
                    continue
                # 3. 【关键】跳过 pip 选项 (如 --extra-index-url)，constraint 文件不支持这些
                if line.startswith('-'):
                    continue
                
                # 4. 剩下的认为是 "package==version" 格式，加入约束列表
                # 只有带 '==' 的行才是有意义的强约束
                if '==' in line:
                    valid_constraints.append(line)
                    # print(f"   🔒 锁定: {line}") # 调试用，太长可注释

        if not valid_constraints:
            return None

        # 创建临时文件
        temp_fd, temp_path = tempfile.mkstemp(prefix="constraints_", suffix=".txt", text=True)
        with os.fdopen(temp_fd, 'w') as f:
            f.write("\n".join(valid_constraints))
        
        return temp_path

    except Exception as e:
        print(f"❌ 读取依赖文件失败: {e}")
        return None

def install_requirements_stream(req_filename):
    """
    生成器：带版本锁定的安全安装
    """
    req_path = os.path.join(PROJECT_ROOT, req_filename)
    if not os.path.exists(req_path):
        yield f"❌ 找不到依赖文件: {req_filename}\n"
        yield False
        return

    # 1. 生成版本锁定文件 (基于 requirements.txt)
    constraint_path = _create_constraints_from_file()
    
    # 2. 构造 pip 命令
    cmd = [sys.executable, "-m", "pip", "install", "-r", req_path]
    
    # 如果成功生成了约束文件，就加上 -c 参数
    if constraint_path:
        cmd.extend(["-c", constraint_path])
        yield f"🛡️ [System] 已启用严格防御模式 (基于 requirements.txt)\n"
    else:
        yield f"⚠️ [System] 防御模式未启用 (找不到主依赖文件)\n"
    
    yield f"🔧 [CMD] 执行安装...\n"
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding='utf-8',
            errors='replace'
        )

        for line in process.stdout:
            # 拦截冲突报错，翻译成人话
            if "ResolutionImpossible" in line or "Conflict" in line:
                yield f"🛑 [严重警告] 依赖冲突拦截！新插件试图篡改 requirements.txt 中的核心库。\n"
                yield f"   (请手动检查 {req_filename} 中是否有与主环境冲突的版本)\n"
            yield f"   > {line}"

        process.wait()
        
        # 清理临时文件
        if constraint_path and os.path.exists(constraint_path):
            try:
                os.remove(constraint_path)
            except:
                pass
        
        if process.returncode == 0:
            yield f"✅ 依赖 {req_filename} 安装/检查完成！\n"
            yield True
        else:
            yield f"❌ 安装失败 (Return Code: {process.returncode})\n"
            yield False

    except Exception as e:
        yield f"❌ 进程启动异常: {e}\n"
        yield False

def install_requirements(req_filename):
    """兼容旧接口"""
    result = False
    for log in install_requirements_stream(req_filename):
        if isinstance(log, bool): result = log
        else: print(log, end="")
    return result, "操作结束"