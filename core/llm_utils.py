import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# 初始化全局的OpenAI Client
# 默认使用 deepseek 或通义千问等兼容 OpenAI 格式的成熟大模型 API
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY", ""),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com") # 默认给一个常见的 baseUrl 示例
)

def call_llm(system_prompt: str, user_prompt: str, model: str = "deepseek-chat") -> str:
    """
    通用的大模型调用接口，调用成熟大模型 API。
    """
    try:
        if not client.api_key:
            return "[Error: 请在 .env 文件中配置 OPENAI_API_KEY]"
            
        response = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", model),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"LLM Call Error: {e}")
        return f"[Error: LLM Call Failed - {str(e)}]"
