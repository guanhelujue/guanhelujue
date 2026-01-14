import os

def patch_cosyvoice_code(engine_root_dir):
    """
    自动修复 CosyVoice 代码中 torchaudio 版本不兼容的问题
    目标文件: cosyvoice/utils/file_utils.py
    操作: 删除 backend='soundfile' 参数
    """
    # 拼接目标文件路径: src/audio/cosyvoice/cosyvoice/utils/file_utils.py
    target_file = os.path.join(engine_root_dir, "cosyvoice", "utils", "file_utils.py")
    
    if not os.path.exists(target_file):
        # 如果文件找不到，说明源码可能还没下载，或者路径不对，直接忽略
        return None

    try:
        with open(target_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否存在那个报错的参数
        if "backend='soundfile'" in content:
            # 1. 先替换带逗号的情况 ", backend='soundfile'" -> ""
            new_content = content.replace(", backend='soundfile'", "")
            
            # 2. 再替换不带逗号的情况 (防止它是最后一个参数)
            new_content = new_content.replace("backend='soundfile'", "")
            
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            return "✅ [Auto-Fix] 已自动修复 torchaudio 版本兼容性问题 (已移除 backend 参数)。"
            
    except Exception as e:
        return f"⚠️ [Auto-Fix] 尝试修复代码失败: {e}"
    
    return None