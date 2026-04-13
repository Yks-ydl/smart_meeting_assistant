"""
M5 - 主网关与编排服务 (Main Gateway & Orchestrator)

当前仅保留：
  1. 目录批量流式回放 WebSocket 接口（M6 → M3/M4 → M2/M3）
  2. 健康检查接口
  3. 前端静态页面入口
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import httpx
import asyncio
import json
import uvicorn
import os


app = FastAPI(title="M5 - Main Gateway & Orchestrator")

# CORS 支持（便于调试）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# 各微服务地址配置
# ─────────────────────────────────────────────
SERVICES = {
    # M1 - ASR 语音识别
    "asr_transcribe": "http://127.0.0.1:8001/api/v1/asr/transcribe",
    # M2 - 摘要生成
    "summary_generate": "http://127.0.0.1:8002/api/v1/summary/generate",
    "summary_local": "http://127.0.0.1:8002/api/v1/summary/generate_local",
    "summary_llm": "http://127.0.0.1:8002/api/v1/summary/generate_llm",
    "summary_evaluate": "http://127.0.0.1:8002/api/v1/summary/evaluate",
    # M3 - 翻译与待办提取
    "translation_translate": "http://127.0.0.1:8003/api/v1/translation/translate",
    "translation_actions": "http://127.0.0.1:8003/api/v1/translation/extract_actions",
    # M4 - 情感分析
    "sentiment_analyze": "http://127.0.0.1:8004/api/v1/sentiment/analyze",
    # M6 - 音频输入（本地目录处理）
    "audio_process_dir": "http://127.0.0.1:8005/api/v1/audio/process_directory",
    "audio_status": "http://127.0.0.1:8005/api/v1/audio/status",
    "audio_tracks": "http://127.0.0.1:8005/api/v1/audio/tracks",
}


# ─────────────────────────────────────────────
# 通用工具
# ─────────────────────────────────────────────
async def call_service(client: httpx.AsyncClient, url: str, payload: dict, timeout: float = 60.0):
    """通用微服务调用"""
    try:
        print(f"[Gateway] 调用服务: {url}")
        response = await client.post(url, json=payload, timeout=timeout)
        print(f"[Gateway] 响应状态码: {response.status_code}")
        print(f"[Gateway] 响应内容: {response.text[:200]}...")

        if response.status_code != 200:
            return {"status": "error", "error": f"HTTP {response.status_code}", "detail": response.text}

        return response.json()
    except httpx.ConnectError as e:
        print(f"[Gateway] 连接错误: {url} - {str(e)}")
        return {"status": "error", "error": "无法连接到服务", "detail": str(e)}
    except Exception as e:
        print(f"[Gateway] 调用失败: {str(e)}")
        return {"status": "error", "error": str(e)}


async def get_service(client: httpx.AsyncClient, url: str, timeout: float = 30.0):
    """通用 GET 调用"""
    try:
        response = await client.get(url, timeout=timeout)
        return response.json()
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ─────────────────────────────────────────────
# 目录批量流式回放 Pipeline
# ─────────────────────────────────────────────
@app.websocket("/ws/pipeline/dir")
async def ws_pipeline_dir(websocket: WebSocket):
    """
    目录批量处理的 WebSocket 流式接口。
    1. 调用 M6 离线处理全目录
    2. 将 M6 返回的段落按每 5 秒一条的速度流式推给前端
    3. 同步调用 M3 翻译和 M4 情感
    4. 每 30 秒增量提取一次待办
    5. 最后输出摘要和全局待办
    支持前端发送 {"type": "stop"} 提前结束流式回放并生成摘要。
    """
    await websocket.accept()
    stop_event = asyncio.Event()

    async def receive_stop():
        """并发监听前端发来的 stop 指令"""
        try:
            while not stop_event.is_set():
                raw = await websocket.receive_text()
                msg_inner = json.loads(raw)
                if msg_inner.get("type") == "stop":
                    stop_event.set()
        except Exception:
            stop_event.set()

    try:
        data = await websocket.receive_text()
        req_data = json.loads(data)
        session_id = req_data.get("session_id", f"dir-{os.urandom(4).hex()}")
        input_dir = req_data.get("input_dir")
        glob_pattern = req_data.get("glob_pattern", "*.m4a")
        target_lang = req_data.get("target_lang") or "en"
        enable_translation = req_data.get("enable_translation", True)
        enable_actions = req_data.get("enable_actions", True)
        enable_sentiment = req_data.get("enable_sentiment", True)

        await websocket.send_json({"type": "info", "message": "⏳ 阶段 1/3: 正在调用 M6 批量处理音频目录，这可能需要几分钟..."})

        # 启动后台任务监听 stop 指令
        stop_task = asyncio.create_task(receive_stop())

        async with httpx.AsyncClient() as client:
            audio_payload = {
                "session_id": session_id,
                "input_dir": input_dir,
                "glob_pattern": glob_pattern,
                "recursive": False,
            }
            audio_result = await call_service(client, SERVICES["audio_process_dir"], audio_payload, timeout=600.0)

            if audio_result.get("status") == "error":
                await websocket.send_json({"type": "error", "message": f"M6 处理失败: {audio_result}"})
                stop_task.cancel()
                return

            merged_transcript = audio_result.get("merged_transcript", [])
            full_text = audio_result.get("full_text", "")

            if not merged_transcript:
                await websocket.send_json({"type": "error", "message": "未提取到任何转录文本"})
                stop_task.cancel()
                return

            await websocket.send_json({"type": "info", "message": "✅ 阶段 1 完成！开始流式回放分析结果 (每5秒输出一段)..."})

            action_window_start = None
            action_window_texts: list[str] = []
            accumulated_texts: list[str] = []

            for seg in merged_transcript:
                if stop_event.is_set():
                    break

                text = seg.get("corrected_text") or seg.get("text", "")
                speaker = seg.get("speaker_label", "Unknown")
                start_time = float(seg.get("start_time") or 0.0)
                end_time = float(seg.get("end_time") or 0.0)

                if action_window_start is None:
                    action_window_start = start_time

                if not text.strip():
                    continue

                action_window_texts.append(f"{speaker}: {text}")
                accumulated_texts.append(f"{speaker}: {text}")

                await websocket.send_json({
                    "type": "asr_result",
                    "data": {
                        "speaker": speaker,
                        "text": text,
                        "start_time": start_time,
                        "end_time": end_time
                    }
                })

                sent_res = None
                trans_res = None
                tasks = []
                if enable_sentiment:
                    tasks.append(asyncio.create_task(
                        call_service(client, SERVICES["sentiment_analyze"], {"session_id": session_id, "speaker": speaker, "text": text})
                    ))
                if enable_translation:
                    tasks.append(asyncio.create_task(
                        call_service(client, SERVICES["translation_translate"], {"session_id": session_id, "text": text, "target_lang": target_lang})
                    ))
                if tasks:
                    results = await asyncio.gather(*tasks)
                    idx = 0
                    if enable_sentiment:
                        sent_res = results[idx]
                        idx += 1
                    if enable_translation:
                        trans_res = results[idx]

                    await websocket.send_json({
                        "type": "analysis_result",
                        "data": {
                            "sentiment": sent_res,
                            "translation": trans_res
                        }
                    })

                if enable_actions and action_window_start is not None and end_time - action_window_start >= 30.0 and action_window_texts:
                    window_text = "\n".join(action_window_texts)
                    action_res = await call_service(
                        client,
                        SERVICES["translation_actions"],
                        {"session_id": session_id, "text": window_text}
                    )
                    await websocket.send_json({
                        "type": "action_result",
                        "data": {
                            "actions": action_res,
                            "window_start": action_window_start,
                            "window_end": end_time
                        }
                    })
                    action_window_start = end_time
                    action_window_texts = []

                # 每段等待 5 秒，但允许被 stop 提前中断（每秒检查一次）
                for _ in range(5):
                    if stop_event.is_set():
                        break
                    await asyncio.sleep(1)

                if stop_event.is_set():
                    break

            stop_task.cancel()

            # 提前结束时仍保留 action_window_texts 中的剩余片段
            if enable_actions and action_window_texts:
                final_window_end = float(merged_transcript[-1].get("end_time") or 0.0)
                action_res = await call_service(
                    client,
                    SERVICES["translation_actions"],
                    {"session_id": session_id, "text": "\n".join(action_window_texts)}
                )
                await websocket.send_json({
                    "type": "action_result",
                    "data": {
                        "actions": action_res,
                        "window_start": action_window_start,
                        "window_end": final_window_end
                    }
                })

            await websocket.send_json({"type": "info", "message": "⏳ 阶段 3/3: 所有片段输出完毕，正在生成全局摘要与待办..."})

            # 若提前结束，则使用已处理片段的文本生成摘要
            summary_input = "\n".join(accumulated_texts) if (stop_event.is_set() and accumulated_texts) else full_text

            summary_task = asyncio.create_task(call_service(client, SERVICES["summary_generate"], {"session_id": session_id, "text": summary_input}))
            if enable_actions:
                action_task = asyncio.create_task(call_service(client, SERVICES["translation_actions"], {"session_id": session_id, "text": summary_input}))
                summary_res, action_res = await asyncio.gather(summary_task, action_task)
            else:
                summary_res = await summary_task
                action_res = None

            await websocket.send_json({
                "type": "meeting_end_report",
                "data": {
                    "summary": summary_res,
                    "actions": action_res
                }
            })
    except WebSocketDisconnect:
        print("[Gateway] Directory stream disconnected")
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


# ─────────────────────────────────────────────
# 健康检查
# ─────────────────────────────────────────────
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "M5 - Gateway & Orchestrator"}


@app.get("/health/all")
async def health_check_all():
    """检查所有微服务的健康状态"""
    service_urls = {
        "M1_ASR": "http://127.0.0.1:8001/health",
        "M2_Summary": "http://127.0.0.1:8002/health",
        "M3_Translation": "http://127.0.0.1:8003/health",
        "M4_Sentiment": "http://127.0.0.1:8004/health",
        "M6_Audio": "http://127.0.0.1:8005/health",
    }
    results = {}
    async with httpx.AsyncClient() as client:
        for name, url in service_urls.items():
            try:
                resp = await client.get(url, timeout=5.0)
                results[name] = resp.json()
            except Exception as e:
                results[name] = {"status": "unreachable", "error": str(e)}
    return {"status": "ok", "services": results}


# ─────────────────────────────────────────────
# 静态文件服务（前端页面）
# ─────────────────────────────────────────────
static_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")

@app.get("/")
async def read_root():
    """访问根路径时返回前端页面"""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Welcome to AI Meeting Assistant API", "docs": "/docs"}


# 挂载静态文件目录（用于 CSS/JS 等资源）
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
