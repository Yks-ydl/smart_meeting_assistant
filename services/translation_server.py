from fastapi import FastAPI
from pydantic import BaseModel
import sys
import os
import uvicorn

# 将项目根目录加入 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.llm_utils import call_llm

app = FastAPI(title="M3 - Translation & Action Extraction Service")

class TextContent(BaseModel):
    session_id: str
    text: str
    target_lang: str = "en"  # 目标语言，默认英文

@app.post("/api/v1/translation/translate")
async def translate_text(content: TextContent):
    """
    多语言实时机器翻译 (MT)
    """
    system_prompt = f"你是一个专业的同声传译员。请将以下文本翻译成{content.target_lang}。只输出翻译结果。"
    
    translated_text = call_llm(system_prompt=system_prompt, user_prompt=content.text)
        
    return {
        "status": "success",
        "session_id": content.session_id,
        "translated_text": translated_text
    }

@app.post("/api/v1/translation/extract_actions")
async def extract_actions(content: TextContent):
    """
    上下文感知段落摘要事项提取 (Action Items Extraction)
    提取会议中的待办事项
    """
    system_prompt = "你是一个专业的项目经理助手。请从以下会议记录中提取具体的待办事项（Action Items），如果没有待办事项则返回空列表。请以 Markdown 列表形式输出。"
    
    actions_result = call_llm(system_prompt=system_prompt, user_prompt=content.text)
        
    return {
        "status": "success",
        "session_id": content.session_id,
        "action_items": actions_result
    }

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "M3 - Translation & Action Extraction"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
