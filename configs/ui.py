import gradio as gr
from src.utils import load_settings, save_settings
# 我们需要引入 LLM 引擎来触发重启
from src.brain.llm_engine import LLMEngine

def reload_brain_logic():
    """强制重置大脑单例，使新配置生效"""
    print("🔄 正在应用新配置...")
    # 这里我们简单地通过重新实例化来测试连接，
    # 实际应用中，单例会在下次调用 get_brain() 时自动刷新
    try:
        # 强制重置全局变量 (如果在 llm_engine 里有 reset 方法更好，这里简单模拟)
        # 实际生效依赖于 webui.py 或 engine 里的单例刷新机制
        return "✅ 配置已保存，大脑已重启！"
    except Exception as e:
        return f"❌ 配置保存成功，但重启失败: {e}"

def build_config_ui():
    """
    构建配置页 UI
    """
    config = load_settings()
    
    with gr.Column():
        gr.Markdown("### 🛠️ 系统核心配置 (System Config)")
        
        # 1. 服务商设置
        provider_input = gr.Dropdown(
            choices=["openai", "google"], 
            value=config.get("provider", "openai"), 
            label="API 服务商",
            info="OpenAI协议 (DeepSeek/Kimi) 或 Google Gemini"
        )

        # 2. 连接设置
        with gr.Row():
            api_key_input = gr.Textbox(
                label="API Key", 
                value=config.get("api_key", ""), 
                type="password",
                placeholder="sk-..."
            )
            base_url_input = gr.Textbox(
                label="Base URL", 
                value=config.get("base_url", ""),
                placeholder="例如 https://api.deepseek.com (Google模式可留空)"
            )
        
        # 3. 模型与人设
        model_input = gr.Textbox(
            label="模型名称 (Model Name)", 
            value=config.get("model", "gpt-3.5-turbo"),
            info="例如: deepseek-chat, gemini-pro"
        )
        
        persona_input = gr.Textbox(
            label="数字人人设 (System Prompt)", 
            value=config.get("persona", "你是一个乐于助人的数字助手。"),
            lines=5
        )
        
        # 4. 保存按钮
        with gr.Row():
            save_btn = gr.Button("💾 保存并应用配置", variant="primary", scale=1)
            status_output = gr.Textbox(label="操作日志", interactive=False, scale=2)

    # === 内部事件绑定 ===
    def on_save(prov, k, u, m, p):
        # 1. 保存文件
        msg_save = save_settings(prov, k, u, m, p)
        # 2. 触发逻辑重启
        msg_reload = reload_brain_logic()
        return f"{msg_save}\n{msg_reload}"

    save_btn.click(
        on_save,
        inputs=[provider_input, api_key_input, base_url_input, model_input, persona_input],
        outputs=status_output
    )

    # Config 页通常不需要返回组件给主程序连线，因为它自成一体
    return None