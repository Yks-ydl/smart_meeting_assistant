from fastapi import FastAPI
from pydantic import BaseModel
import sys
import os
import uvicorn

import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.llm_utils import call_llm

app = FastAPI(title="M4 - Sentiment & Engagement Analysis Service")

class Utterance(BaseModel):
    session_id: str
    speaker: str
    text: str

@app.post("/api/v1/sentiment/analyze")
async def analyze_sentiment(utterance: Utterance):
    """
    会议情感与参与度分析
    捕捉同意/分歧/犹豫等交互信号
    """
    system_prompt = """
    你是一个心理学与人际沟通专家。请分析以下会议发言的情感色彩和交互信号。
    请返回一个JSON格式的结果，包含以下字段：
    - sentiment: "positive" / "neutral" / "negative"
    - signal: "agreement" (同意) / "disagreement" (分歧) / "hesitation" (犹豫) / "neutral" (中立)
    - explanation: 简短的分析理由
    """
    user_prompt = f"发言人 {utterance.speaker} 说道: \"{utterance.text}\""
    
    llm_response = call_llm(system_prompt=system_prompt, user_prompt=user_prompt)
    
    # 解析 JSON
    analysis_result = {
        "sentiment": "neutral",
        "signal": "neutral",
        "explanation": "解析失败"
    }
    try:
        clean_json = llm_response.replace('```json', '').replace('```', '').strip()
        analysis_result = json.loads(clean_json)
    except Exception as e:
        print(f"Sentiment JSON parse error: {e}")
        analysis_result["explanation"] = f"JSON解析错误: {llm_response}"
        
    return {
        "status": "success",
        "session_id": utterance.session_id,
        "speaker": utterance.speaker,
        "analysis": analysis_result
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)
