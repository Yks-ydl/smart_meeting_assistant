from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio
import json
import os
import uvicorn
from dataclasses import dataclass
from pathlib import Path

app = FastAPI(title="M5 - Main Gateway & Orchestrator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def resolve_frontend_dist_dir() -> Path:
    """Use a single in-repo frontend location to avoid cross-project path coupling."""
    return Path(__file__).resolve().parents[1] / "frontend" / "dist"


frontend_dir = resolve_frontend_dist_dir()
if frontend_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/")
    async def serve_frontend():
        """返回前端主页"""
        return FileResponse(str(frontend_dir / "index.html"))


def build_service_endpoints() -> dict[str, str]:
    # Keep service URLs in one place so local and Colab targets share the same mapping logic.
    return {
        "asr": "http://127.0.0.1:8001/api/v1/asr/transcribe",
        "summary": os.getenv(
            "SUMMARY_SERVICE_URL",
            "http://127.0.0.1:8002/api/v1/summary/generate",
        ),
        "translation": "http://127.0.0.1:8003/api/v1/translation/translate",
        "action": "http://127.0.0.1:8003/api/v1/translation/extract_actions",
        "sentiment": "http://127.0.0.1:8004/api/v1/sentiment/analyze",
        "audio_start": "http://127.0.0.1:8005/api/v1/audio/start_capture",
        "audio_stop": "http://127.0.0.1:8005/api/v1/audio/stop_capture",
        "audio_upload": "http://127.0.0.1:8005/api/v1/audio/upload_multitrack",
        "audio_status": "http://127.0.0.1:8005/api/v1/audio/status",
        "audio_tracks": "http://127.0.0.1:8005/api/v1/audio/tracks",
        "data_status": "http://127.0.0.1:8006/api/v1/data/status",
        "data_stream": "http://127.0.0.1:8006/api/v1/data/stream",
    }


SERVICES = build_service_endpoints()


@dataclass
class SummaryRequestConfig:
    timeout_sec: float
    retries: int
    headers: dict[str, str]


def _parse_float(value: str | None, default_value: float) -> float:
    try:
        return float(value) if value is not None else default_value
    except (TypeError, ValueError):
        return default_value


def _parse_int(value: str | None, default_value: int) -> int:
    try:
        return int(value) if value is not None else default_value
    except (TypeError, ValueError):
        return default_value


def build_summary_request_config() -> SummaryRequestConfig:
    timeout_sec = _parse_float(os.getenv("SUMMARY_REMOTE_TIMEOUT_SEC"), 90.0)
    retries = max(0, _parse_int(os.getenv("SUMMARY_REMOTE_RETRIES"), 1))
    auth_header = os.getenv("SUMMARY_REMOTE_AUTH_HEADER", "Authorization").strip()
    auth_scheme = os.getenv("SUMMARY_REMOTE_AUTH_SCHEME", "Bearer").strip()
    auth_token = os.getenv("SUMMARY_REMOTE_AUTH_TOKEN", "").strip()

    headers: dict[str, str] = {}
    if auth_token:
        headers[auth_header] = (
            f"{auth_scheme} {auth_token}".strip() if auth_scheme else auth_token
        )

    return SummaryRequestConfig(timeout_sec=timeout_sec, retries=retries, headers=headers)


async def call_summary_service(
    client: httpx.AsyncClient,
    summary_url: str,
    payload: dict,
    config: SummaryRequestConfig,
) -> dict:
    attempts = config.retries + 1
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            response = await client.post(
                summary_url,
                json=payload,
                timeout=config.timeout_sec,
                headers=config.headers or None,
            )
            return response.json()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(
                f"[Gateway] Summary request failed attempt {attempt}/{attempts} "
                f"url={summary_url}: {exc}"
            )

    return {
        "error": f"summary service request failed after {attempts} attempts: {last_error}"
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


def normalize_target_lang(value: str | None) -> str:
    if not isinstance(value, str):
        return "en"

    head = value.lower().split("-")[0].split("_")[0]
    if head in {"zh", "en", "ja"}:
        return head
    return "en"


async def call_service(
    client: httpx.AsyncClient,
    url: str,
    payload: dict | list | None = None,
    method: str = "POST",
):
    try:
        if method == "POST":
            response = await client.post(url, json=payload, timeout=30.0)
        else:
            response = await client.get(url, timeout=30.0)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def parse_timestamp_to_seconds(value, fallback: float) -> float:
    if isinstance(value, (int, float)):
        return max(0.0, float(value))

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return fallback

        try:
            return max(0.0, float(text))
        except ValueError:
            pass

        parts = text.split(":")
        if len(parts) in {2, 3}:
            try:
                nums = [float(part) for part in parts]
            except ValueError:
                nums = []

            if nums:
                if len(nums) == 2:
                    minutes, seconds = nums
                    return max(0.0, minutes * 60 + seconds)
                hours, minutes, seconds = nums
                return max(0.0, hours * 3600 + minutes * 60 + seconds)

    return fallback


def append_sentiment_turn(sentiment_turns_ref: dict, raw_turn: dict):
    # Centralize turn normalization so demo/realtime paths share identical M4 input format.
    text = str(raw_turn.get("corrected_text") or raw_turn.get("text") or "").strip()
    if not text:
        return

    speaker = str(raw_turn.get("speaker_label") or raw_turn.get("speaker") or "").strip()
    if not speaker:
        speaker = "Unknown"

    language = normalize_target_lang(str(raw_turn.get("language") or "zh"))

    fallback_start = float(len(sentiment_turns_ref["items"]))
    start_time = parse_timestamp_to_seconds(
        raw_turn.get("start_time", raw_turn.get("timestamp")), fallback_start
    )
    end_time = parse_timestamp_to_seconds(raw_turn.get("end_time"), start_time + 1.5)
    if end_time <= start_time:
        end_time = start_time + 1.0

    sentiment_turns_ref["items"].append(
        {
            "text": str(raw_turn.get("text") or text),
            "corrected_text": text,
            "start_time": round(start_time, 3),
            "end_time": round(end_time, 3),
            "speaker_label": speaker,
            "language": language,
        }
    )


async def process_translation_async(
    client: httpx.AsyncClient,
    session_id: str,
    subtitle_id: str,
    text: str,
    target_lang: str,
    websocket: WebSocket,
):
    """异步处理翻译，不阻塞字幕流"""
    try:
        translation_res = await call_service(
            client,
            SERVICES["translation"],
            {
                "session_id": session_id,
                "text": text,
                "target_lang": target_lang,
            },
        )
        await manager.send_message(
            {
                "type": "translation",
                "data": {
                    "subtitle_id": subtitle_id,
                    "translated_text": translation_res.get("translated_text", ""),
                },
            },
            websocket,
        )
    except Exception as e:
        print(f"[Gateway] Translation error for subtitle {subtitle_id}: {e}")


async def stream_demo_data(
    client: httpx.AsyncClient,
    session_id: str,
    websocket: WebSocket,
    full_text_ref: dict,
    target_lang_ref: dict,
    sentiment_turns_ref: dict,
):
    """从数据服务获取 VCSum 字幕流并推送"""
    try:
        status_res = await call_service(
            client,
            SERVICES["data_status"],
            method="GET",
        )

        if status_res.get("error"):
            await manager.send_message(
                {
                    "type": "error",
                    "data": {
                        "message": f"M7 数据服务不可达，请检查 8006 服务：{status_res['error']}"
                    },
                },
                websocket,
            )
            return

        if not status_res.get("is_loaded"):
            await manager.send_message(
                {
                    "type": "error",
                    "data": {
                        "message": "M7 数据服务尚未加载完成，请稍后重试开始会议。"
                    },
                },
                websocket,
            )
            return

        async with client.stream(
            "GET", SERVICES["data_stream"], timeout=300.0
        ) as response:
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                try:
                    data = json.loads(line[6:])
                    if data.get("type") == "subtitle":
                        sub = data["data"]
                        # 为每条字幕生成唯一ID
                        subtitle_id = f"{session_id}_{hash(sub['text'] + str(sub.get('timestamp', '')))}"
                        sub["id"] = subtitle_id

                        # 立即发送字幕，不等待翻译
                        await manager.send_message(
                            {"type": "subtitle", "data": sub}, websocket
                        )
                        full_text_ref["text"] += f"[{sub['speaker']}]: {sub['text']}\n"

                        append_sentiment_turn(sentiment_turns_ref, sub)

                        # 翻译改为异步执行，不阻塞下一条字幕
                        asyncio.create_task(
                            process_translation_async(
                                client,
                                session_id,
                                subtitle_id,
                                sub["text"],
                                target_lang_ref["value"],
                                websocket,
                            )
                        )
                    elif data.get("type") == "stream_complete":
                        await manager.send_message(
                            {
                                "type": "stream_complete",
                                "data": {"total": data.get("total", 0)},
                            },
                            websocket,
                        )
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"[Gateway] Demo stream error: {e}")
        try:
            await manager.send_message(
                {
                    "type": "error",
                    "data": {"message": f"字幕流异常，请检查 M7 数据服务: {e}"},
                },
                websocket,
            )
        except Exception:
            pass


@app.websocket("/ws/meeting/{session_id}")
async def meeting_endpoint(websocket: WebSocket, session_id: str):
    """
    前端通过 WebSocket 接入，发送音频/指令，接收分析结果
    """
    await manager.connect(websocket)
    full_text_ref = {"text": ""}  # 用于存储会议全文
    target_lang_ref = {"value": "en"}
    sentiment_turns_ref = {"items": []}
    sentiment_enabled_ref = {"value": True}

    try:
        async with httpx.AsyncClient() as client:
            while True:
                # 接收前端发送的消息（如音频分片）
                data = await websocket.receive_text()

                # 假设前端发来的是一个简单的控制指令或 base64 音频
                message = json.loads(data)

                if message.get("type") == "start_meeting":
                    mode = message.get("mode", "demo")
                    full_text_ref["text"] = ""
                    sentiment_turns_ref["items"] = []
                    sentiment_enabled_ref["value"] = bool(
                        message.get("sentiment_enabled", True)
                    )
                    target_lang_ref["value"] = normalize_target_lang(
                        message.get("target_lang")
                    )
                    await manager.send_message(
                        {
                            "type": "meeting_started",
                            "data": {
                                "session_id": session_id,
                                "mode": mode,
                                "target_lang": target_lang_ref["value"],
                            },
                        },
                        websocket,
                    )

                    if mode == "demo":
                        asyncio.create_task(
                            stream_demo_data(
                                client,
                                session_id,
                                websocket,
                                full_text_ref,
                                target_lang_ref,
                                sentiment_turns_ref,
                            )
                        )

                elif message.get("type") == "audio_chunk":
                    # 1. Pipeline 阶段一：调用 ASR
                    audio_base64 = message.get("data", "")

                    # 为了避免无声音频段引起空转写，也可以在网关或前端做VAD，这里暂不处理
                    asr_payload = {
                        "audio_base64": audio_base64,
                        "session_id": session_id,
                    }
                    asr_result = await call_service(
                        client, SERVICES["asr"], asr_payload
                    )

                    print(f"ASR Result: {asr_result}")  # 增加日志输出以便调试

                    # 检查是否有有效转录
                    if "error" in asr_result:
                        # 通知前端 ASR 服务出现问题
                        await manager.send_message(
                            {
                                "type": "asr_result",
                                "data": {
                                    "speaker": "System",
                                    "text": f"系统提示：ASR服务未连接或异常 ({asr_result['error']})",
                                },
                            },
                            websocket,
                        )
                    elif (
                        "text" in asr_result
                        and asr_result["text"]
                        and asr_result["text"] != "[未识别到有效语音]"
                    ):
                        speaker = asr_result["speaker"]
                        text = asr_result["text"]

                        # 立即向前端推送实时转录结果
                        await manager.send_message(
                            {"type": "asr_result", "data": asr_result}, websocket
                        )

                        append_sentiment_turn(
                            sentiment_turns_ref,
                            {
                                "text": text,
                                "corrected_text": asr_result.get("corrected_text"),
                                "speaker_label": speaker,
                                "start_time": asr_result.get("start_time"),
                                "end_time": asr_result.get("end_time"),
                                "language": asr_result.get("language"),
                            },
                        )

                        # 2. Pipeline 阶段二：调用翻译微服务
                        translation_payload = {
                            "session_id": session_id,
                            "text": text,
                            "target_lang": target_lang_ref["value"],
                        }

                        translation_res = await call_service(
                            client, SERVICES["translation"], translation_payload
                        )

                        # 推送翻译结果
                        await manager.send_message(
                            {
                                "type": "analysis_result",
                                "data": {
                                    "translation": translation_res,
                                },
                            },
                            websocket,
                        )

                elif message.get("type") == "end_meeting":
                    full_text = (
                        message.get("full_text")
                        or full_text_ref["text"]
                        or "这是一个模拟的完整会议记录..."
                    )
                    summary_payload = {"session_id": session_id, "text": full_text}
                    action_payload = {"session_id": session_id, "text": full_text}
                    sentiment_payload = sentiment_turns_ref["items"]
                    summary_config = build_summary_request_config()

                    summary_task = asyncio.create_task(
                        call_summary_service(
                            client=client,
                            summary_url=SERVICES["summary"],
                            payload=summary_payload,
                            config=summary_config,
                        )
                    )
                    action_task = asyncio.create_task(
                        call_service(client, SERVICES["action"], action_payload)
                    )

                    if sentiment_enabled_ref["value"]:
                        sentiment_task = asyncio.create_task(
                            call_service(client, SERVICES["sentiment"], sentiment_payload)
                        )
                        summary_res, action_res, sentiment_res = await asyncio.gather(
                            summary_task, action_task, sentiment_task
                        )
                    else:
                        summary_res, action_res = await asyncio.gather(
                            summary_task, action_task
                        )
                        sentiment_res = None

                    await manager.send_message(
                        {
                            "type": "meeting_end_report",
                            "data": {
                                "summary": summary_res,
                                "actions": action_res,
                                "sentiment": sentiment_res,
                            },
                        },
                        websocket,
                    )

                    if sentiment_enabled_ref["value"] and sentiment_res is not None:
                        await manager.send_message(
                            {"type": "sentiment", "data": sentiment_res}, websocket
                        )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Session {session_id} disconnected")


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Gateway is running"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
