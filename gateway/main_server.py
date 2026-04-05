from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import httpx
import asyncio
import json
import uvicorn
import os

app = FastAPI(title="M5 - Main Gateway & Orchestrator")

# 挂载前端静态文件
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
async def serve_frontend():
    """返回前端主页"""
    return FileResponse(os.path.join(frontend_dir, "index.html"))

# 各微服务的本地地址配置
SERVICES = {
    "asr": "http://127.0.0.1:8001/api/v1/asr/transcribe",
    "summary": "http://127.0.0.1:8002/api/v1/summary/generate",
    "translation": "http://127.0.0.1:8003/api/v1/translation/translate",
    "action": "http://127.0.0.1:8003/api/v1/translation/extract_actions",
    "sentiment": "http://127.0.0.1:8004/api/v1/sentiment/analyze",
    "audio_start": "http://127.0.0.1:8005/api/v1/audio/start_capture",
    "audio_stop": "http://127.0.0.1:8005/api/v1/audio/stop_capture",
    "audio_upload": "http://127.0.0.1:8005/api/v1/audio/upload_multitrack",
    "audio_status": "http://127.0.0.1:8005/api/v1/audio/status",
    "audio_tracks": "http://127.0.0.1:8005/api/v1/audio/tracks",
}

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

manager = ConnectionManager()

async def call_service(client: httpx.AsyncClient, url: str, payload: dict):
    try:
        response = await client.post(url, json=payload, timeout=30.0)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

@app.websocket("/ws/meeting/{session_id}")
async def meeting_endpoint(websocket: WebSocket, session_id: str):
    """
    前端通过 WebSocket 接入，发送音频/指令，接收分析结果
    """
    await manager.connect(websocket)
    try:
        async with httpx.AsyncClient() as client:
            while True:
                # 接收前端发送的消息（如音频分片）
                data = await websocket.receive_text()
                
                # 假设前端发来的是一个简单的控制指令或 base64 音频
                message = json.loads(data)
                
                if message.get("type") == "audio_chunk":
                    # 1. Pipeline 阶段一：调用 ASR
                    audio_base64 = message.get("data", "")
                    
                    # 为了避免无声音频段引起空转写，也可以在网关或前端做VAD，这里暂不处理
                    asr_payload = {"audio_base64": audio_base64, "session_id": session_id}
                    asr_result = await call_service(client, SERVICES["asr"], asr_payload)
                    
                    print(f"ASR Result: {asr_result}") # 增加日志输出以便调试
                    
                    # 检查是否有有效转录
                    if "error" in asr_result:
                        # 通知前端 ASR 服务出现问题
                        await manager.send_message({
                            "type": "asr_result",
                            "data": {
                                "speaker": "System",
                                "text": f"系统提示：ASR服务未连接或异常 ({asr_result['error']})"
                            }
                        }, websocket)
                    elif "text" in asr_result and asr_result["text"] and asr_result["text"] != "[未识别到有效语音]":
                        speaker = asr_result["speaker"]
                        text = asr_result["text"]
                        
                        # 立即向前端推送实时转录结果
                        await manager.send_message({
                            "type": "asr_result",
                            "data": asr_result
                        }, websocket)
                        
                        # 2. Pipeline 阶段二：并行调用下游微服务
                        # - 情感分析
                        sentiment_payload = {"session_id": session_id, "speaker": speaker, "text": text}
                        # - 翻译
                        translation_payload = {"session_id": session_id, "text": text, "target_lang": "en"}
                        
                        sentiment_task = asyncio.create_task(call_service(client, SERVICES["sentiment"], sentiment_payload))
                        translation_task = asyncio.create_task(call_service(client, SERVICES["translation"], translation_payload))
                        
                        sentiment_res, translation_res = await asyncio.gather(sentiment_task, translation_task)
                        
                        # 推送情感与翻译结果
                        await manager.send_message({
                            "type": "analysis_result",
                            "data": {
                                "sentiment": sentiment_res,
                                "translation": translation_res
                            }
                        }, websocket)
                        
                elif message.get("type") == "end_meeting":
                    # 3. 会议结束，触发总结和待办提取
                    full_text = message.get("full_text", "这是一个模拟的完整会议记录...")
                    summary_payload = {"session_id": session_id, "text": full_text}
                    action_payload = {"session_id": session_id, "text": full_text}
                    
                    summary_task = asyncio.create_task(call_service(client, SERVICES["summary"], summary_payload))
                    action_task = asyncio.create_task(call_service(client, SERVICES["action"], action_payload))
                    
                    summary_res, action_res = await asyncio.gather(summary_task, action_task)
                    
                    await manager.send_message({
                        "type": "meeting_end_report",
                        "data": {
                            "summary": summary_res,
                            "actions": action_res
                        }
                    }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Session {session_id} disconnected")

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Gateway is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
