from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import sys
import os
import json
import base64
import tempfile

# 解决 Windows 环境下常见的 OMP 冲突报错
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from faster_whisper import WhisperModel

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.llm_utils import call_llm

app = FastAPI(title="M1 - ASR & Speech Processing Service")

# 初始化 Faster Whisper 模型 (首次运行会自动下载模型权重)
# 为了兼顾速度和准确率，默认使用 'small' 或 'base' 模型。如果在有GPU的机器上可改为 "cuda"
print("Loading Whisper Model...")
model = WhisperModel("base", device="cpu", compute_type="int8")
print("Whisper Model Loaded.")

class AudioData(BaseModel):
    # 接收 base64 编码的音频数据 (通常是 webm 或 wav 格式)
    audio_base64: str = ""
    session_id: str

@app.post("/api/v1/asr/transcribe")
async def transcribe(audio: AudioData):
    """
    接收真实的音频数据流（Base64），使用 Faster-Whisper 进行真实的语音转文字。
    """
    if not audio.audio_base64 or audio.audio_base64 == "base64_encoded_audio_placeholder_string":
        # 兼容旧的“模拟发送”逻辑，如果没有真实音频，依然用大模型 mock
        system_prompt = """你是一个会议记录生成器。请随机生成一句短小精悍的中文会议发言（不超过30字），并且随机指定一个发言人名字（如：张总、李工、王经理）。
请必须返回严格的 JSON 格式，包含两个字段："speaker" 和 "text"."""
        user_prompt = "请生成下一句会议发言。"
        llm_response = call_llm(system_prompt=system_prompt, user_prompt=user_prompt)
        
        speaker = "Unknown"
        text = "..."
        try:
            clean_json = llm_response.replace('```json', '').replace('```', '').strip()
            data = json.loads(clean_json)
            speaker = data.get("speaker", "Speaker_A")
            text = data.get("text", "未能解析文本")
        except Exception as e:
            text = f"LLM生成内容解析失败: {llm_response}"

        return {
            "status": "success",
            "session_id": audio.session_id,
            "speaker": speaker,
            "text": text
        }
    
    # ---------------- 真实语音处理流程 ----------------
    text = ""
    speaker = "Speaker_1" # 简化版暂不实现声纹分离，统一分配为Speaker_1
    
    try:
        # 解码 Base64 音频数据
        audio_bytes = base64.b64decode(audio.audio_base64)
        
        # 将音频保存为临时文件，供 whisper 处理
        # 前端 MediaRecorder 录制的通常是 webm 格式
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name

        # 调用 faster-whisper 进行转录
        segments, info = model.transcribe(tmp_path, beam_size=5, language="zh")
        
        for segment in segments:
            text += segment.text + " "
            
        # 清理临时文件
        os.remove(tmp_path)
        
        text = text.strip()
        if not text:
            text = "[未识别到有效语音]"
            
    except Exception as e:
        print(f"ASR Error: {e}")
        text = f"[音频解析错误: {str(e)}]"

    return {
        "status": "success",
        "session_id": audio.session_id,
        "speaker": speaker,
        "text": text
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
