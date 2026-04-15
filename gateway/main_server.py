import sys
from pathlib import Path

# Ensure project root is on sys.path so `from gateway.xxx` works when run as a script
_project_root = str(Path(__file__).resolve().parents[1])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio
import json
import os
import uvicorn
from dataclasses import dataclass, field
from pathlib import Path

from core.chinese_utils import (
    normalize_simplified_chinese_payload,
    normalize_simplified_chinese_text,
)

DEFAULT_AUDIO_GLOB_PATTERN = "*"
DEFAULT_PIPELINE_REPLAY_DELAY_SEC = 5.0

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


def resolve_project_root() -> Path:
    """Keep project-root resolution in one place for gateway-side path handling."""
    return Path(__file__).resolve().parents[1]


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
        "audio_process_directory": "http://127.0.0.1:8005/api/v1/audio/process_directory",
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
        if websocket in self.active_connections:
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


def coerce_bool(value, default: bool) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False

    return default


def resolve_demo_audio_input_dir(input_dir: str | None) -> Path:
    """Resolve demo-mode audio input from request, env, or repo-local sample directory."""
    raw_value = (input_dir or "").strip() or os.getenv("MEETING_AUDIO_INPUT_DIR", "").strip()
    candidate = Path(raw_value).expanduser() if raw_value else resolve_project_root() / "audio"
    if not candidate.is_absolute():
        candidate = resolve_project_root() / candidate
    return candidate


def build_audio_tracks_url(session_id: str) -> str:
    return f"{SERVICES['audio_tracks'].rstrip('/')}/{session_id}"


def normalize_speaker_and_text(speaker: str, text: str) -> tuple[str, str]:
    """Keep speaker/text normalization in one place for realtime and batch flows."""
    normalized_speaker = normalize_simplified_chinese_text(speaker.strip()) or "Unknown"
    normalized_text = normalize_simplified_chinese_text(text.strip())
    return normalized_speaker, normalized_text


def normalize_gateway_payload(payload):
    """Normalize outbound gateway payloads once so every UI surface stays in Simplified Chinese."""
    return normalize_simplified_chinese_payload(payload)


def build_demo_audio_request(
    session_id: str,
    input_dir: str | None,
    glob_pattern: str | None = None,
    recursive: bool | None = None,
) -> dict:
    # Keep one request builder so gateway config parsing and tests share the same defaults.
    resolved_glob_pattern = (
        glob_pattern.strip()
        if isinstance(glob_pattern, str) and glob_pattern.strip()
        else os.getenv("MEETING_AUDIO_GLOB_PATTERN", DEFAULT_AUDIO_GLOB_PATTERN)
    )
    resolved_recursive = (
        recursive
        if isinstance(recursive, bool)
        else os.getenv("MEETING_AUDIO_RECURSIVE", "false").strip().lower()
        in {"1", "true", "yes", "on"}
    )
    return {
        "session_id": session_id,
        "input_dir": str(resolve_demo_audio_input_dir(input_dir)),
        "glob_pattern": resolved_glob_pattern,
        "recursive": resolved_recursive,
    }


def build_subtitle_from_audio_segment(session_id: str, index: int, segment: dict) -> dict:
    """Reuse one normalization path so all M6 transcript items look like demo subtitles."""
    speaker, text = normalize_speaker_and_text(
        str(segment.get("speaker_label") or segment.get("speaker") or "Unknown"),
        str(segment.get("corrected_text") or segment.get("text") or ""),
    )
    start_time = parse_timestamp_to_seconds(segment.get("start_time"), float(index))
    return {
        "id": f"{session_id}_{index}_{segment.get('source_channel', 'audio')}",
        "speaker": speaker,
        "text": text,
        "timestamp": f"{start_time:.3f}",
        "language": normalize_target_lang(str(segment.get("language") or "zh")),
        "source": "audio_directory",
    }


def build_sentiment_turn_from_audio_segment(subtitle: dict, segment: dict) -> dict:
    """Keep audio-directory sentiment input aligned with the subtitle text shown to users."""
    return {
        "text": subtitle["text"],
        "corrected_text": subtitle["text"],
        "speaker_label": subtitle["speaker"],
        "start_time": segment.get("start_time"),
        "end_time": segment.get("end_time"),
        "language": subtitle["language"],
    }


async def call_service(
    client: httpx.AsyncClient,
    url: str,
    payload: dict | list | None = None,
    method: str = "POST",
    timeout: float = 30.0,
):
    try:
        if method == "POST":
            response = await client.post(url, json=payload, timeout=timeout)
        else:
            response = await client.get(url, timeout=timeout)
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
    speaker, text = normalize_speaker_and_text(
        str(raw_turn.get("speaker_label") or raw_turn.get("speaker") or "Unknown"),
        str(raw_turn.get("corrected_text") or raw_turn.get("text") or ""),
    )
    if not text:
        return

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
            "text": normalize_simplified_chinese_text(str(raw_turn.get("text") or text)),
            "corrected_text": text,
            "start_time": round(start_time, 3),
            "end_time": round(end_time, 3),
            "speaker_label": speaker,
            "language": language,
        }
    )


def build_empty_sentiment_report() -> dict:
    return {
        "overall_summary": {
            "total_turns": 0,
            "dominant_signals": [],
            "atmosphere": "Positive/Constructive",
        },
        "speaker_profiles": {},
        "significant_moments": [],
    }


def build_emitted_full_text_line(speaker: str, text: str) -> str:
    return f"[{speaker}]: {text}"


def resolve_pipeline_replay_delay() -> float:
    delay = _parse_float(
        os.getenv("GATEWAY_REPLAY_DELAY_SEC"), DEFAULT_PIPELINE_REPLAY_DELAY_SEC
    )
    return max(0.0, delay)


@dataclass
class DirectoryPipelineRequest:
    session_id: str
    input_dir: str | None
    glob_pattern: str
    target_lang: str
    enable_translation: bool
    enable_actions: bool
    enable_sentiment: bool


@dataclass
class DirectoryPipelineState:
    emitted_full_text_lines: list[str] = field(default_factory=list)
    emitted_sentiment_turns: list[dict] = field(default_factory=list)
    action_window_start: float | None = None
    action_window_texts: list[str] = field(default_factory=list)
    emitted_segments: int = 0

    def emitted_full_text(self) -> str:
        return "\n".join(self.emitted_full_text_lines).strip()


def build_directory_pipeline_request(message: dict) -> DirectoryPipelineRequest:
    return DirectoryPipelineRequest(
        session_id=str(message.get("session_id") or f"session-{os.urandom(4).hex()}"),
        input_dir=(
            str(message.get("input_dir")).strip()
            if message.get("input_dir") is not None and str(message.get("input_dir")).strip()
            else None
        ),
        glob_pattern=(
            str(message.get("glob_pattern")).strip()
            if message.get("glob_pattern") is not None and str(message.get("glob_pattern")).strip()
            else DEFAULT_AUDIO_GLOB_PATTERN
        ),
        target_lang=normalize_target_lang(message.get("target_lang")),
        enable_translation=coerce_bool(message.get("enable_translation"), True),
        enable_actions=coerce_bool(message.get("enable_actions"), True),
        enable_sentiment=coerce_bool(message.get("enable_sentiment"), True),
    )


async def send_directory_pipeline_info(websocket: WebSocket, message: str):
    await websocket.send_json({"type": "info", "message": message})


async def flush_action_window(
    client: httpx.AsyncClient,
    websocket: WebSocket,
    request: DirectoryPipelineRequest,
    state: DirectoryPipelineState,
    window_end: float,
):
    if (
        not request.enable_actions
        or state.action_window_start is None
        or not state.action_window_texts
    ):
        return

    action_res = normalize_gateway_payload(
        await call_service(
            client,
            SERVICES["action"],
            {"session_id": request.session_id, "text": "\n".join(state.action_window_texts)},
        )
    )
    await websocket.send_json(
        {
            "type": "action_result",
            "data": {
                "actions": action_res,
                "window_start": state.action_window_start,
                "window_end": window_end,
            },
        }
    )
    state.action_window_start = window_end
    state.action_window_texts = []


async def finalize_directory_pipeline(
    client: httpx.AsyncClient,
    websocket: WebSocket,
    request: DirectoryPipelineRequest,
    state: DirectoryPipelineState,
):
    emitted_full_text = state.emitted_full_text()

    if state.action_window_texts:
        final_window_end = 0.0
        if state.emitted_sentiment_turns:
            final_window_end = float(
                state.emitted_sentiment_turns[-1].get("end_time") or 0.0
            )
        await flush_action_window(
            client=client,
            websocket=websocket,
            request=request,
            state=state,
            window_end=final_window_end,
        )

    if not emitted_full_text:
        await websocket.send_json(
            {
                "type": "meeting_end_report",
                "data": {
                    "summary": {"summary": "尚无可总结内容"},
                    "actions": {"parsed_actions": [], "action_items": []},
                    "sentiment": build_empty_sentiment_report()
                    if request.enable_sentiment
                    else None,
                },
            }
        )
        return

    await send_directory_pipeline_info(
        websocket,
        "⏳ 阶段 3/3: 所有已输出片段处理完毕，正在生成全局摘要与待办...",
    )

    summary_payload = {"session_id": request.session_id, "text": emitted_full_text}
    summary_task = asyncio.create_task(
        call_summary_service(
            client=client,
            summary_url=SERVICES["summary"],
            payload=summary_payload,
            config=build_summary_request_config(),
        )
    )

    action_task = None
    if request.enable_actions:
        action_task = asyncio.create_task(
            call_service(client, SERVICES["action"], summary_payload)
        )

    sentiment_task = None
    if request.enable_sentiment:
        sentiment_task = asyncio.create_task(
            call_service(client, SERVICES["sentiment"], state.emitted_sentiment_turns)
        )

    summary_res = normalize_gateway_payload(await summary_task)
    action_res = normalize_gateway_payload(await action_task) if action_task else None
    sentiment_res = (
        normalize_gateway_payload(await sentiment_task) if sentiment_task else None
    )

    await websocket.send_json(
        {
            "type": "meeting_end_report",
            "data": {
                "summary": summary_res,
                "actions": action_res,
                "sentiment": sentiment_res,
            },
        }
    )


async def run_directory_pipeline(
    client: httpx.AsyncClient,
    websocket: WebSocket,
    request: DirectoryPipelineRequest,
    stop_requested: asyncio.Event,
):
    await send_directory_pipeline_info(
        websocket,
        "⏳ 阶段 1/3: 正在调用 M6 批量处理音频目录，这可能需要几分钟...",
    )

    audio_payload = build_demo_audio_request(
        session_id=request.session_id,
        input_dir=request.input_dir,
        glob_pattern=request.glob_pattern,
        recursive=False,
    )
    audio_result = await call_service(
        client,
        SERVICES["audio_process_directory"],
        audio_payload,
        timeout=1200.0,
    )

    if audio_result.get("error"):
        await websocket.send_json(
            {
                "type": "error",
                "message": f"目录音频处理失败，请检查 M6 服务：{audio_result['error']}",
            }
        )
        return

    if audio_result.get("status") not in {"success", "partial_success"}:
        await websocket.send_json(
            {
                "type": "error",
                "message": audio_result.get("message", "目录音频处理失败"),
            }
        )
        return

    merged_transcript = audio_result.get("merged_transcript") or []
    if not merged_transcript:
        await websocket.send_json(
            {
                "type": "error",
                "message": "未提取到任何转录文本",
            }
        )
        return

    await send_directory_pipeline_info(
        websocket,
        "✅ 阶段 1 完成！开始流式回放分析结果 (每5秒输出一段)...",
    )

    state = DirectoryPipelineState()
    replay_delay = resolve_pipeline_replay_delay()

    for index, segment in enumerate(merged_transcript):
        if stop_requested.is_set():
            break

        subtitle = build_subtitle_from_audio_segment(request.session_id, index, segment)
        if not subtitle["text"]:
            continue

        start_time = parse_timestamp_to_seconds(segment.get("start_time"), float(index))
        end_time = parse_timestamp_to_seconds(segment.get("end_time"), start_time + 1.5)
        if end_time <= start_time:
            end_time = start_time + 1.0

        subtitle_payload = {
            "id": subtitle["id"],
            "speaker": subtitle["speaker"],
            "text": subtitle["text"],
            "language": subtitle["language"],
            "source": subtitle["source"],
            "timestamp": subtitle["timestamp"],
            "start_time": round(start_time, 3),
            "end_time": round(end_time, 3),
        }
        await websocket.send_json({"type": "asr_result", "data": subtitle_payload})

        state.emitted_segments += 1
        state.emitted_full_text_lines.append(
            build_emitted_full_text_line(subtitle["speaker"], subtitle["text"])
        )
        append_sentiment_turn(
            {"items": state.emitted_sentiment_turns},
            build_sentiment_turn_from_audio_segment(
                subtitle,
                {
                    **segment,
                    "start_time": start_time,
                    "end_time": end_time,
                },
            ),
        )

        if state.action_window_start is None:
            state.action_window_start = start_time
        state.action_window_texts.append(f"{subtitle['speaker']}: {subtitle['text']}")

        translation_task = None
        if request.enable_translation:
            translation_task = asyncio.create_task(
                call_service(
                    client,
                    SERVICES["translation"],
                    {
                        "session_id": request.session_id,
                        "text": subtitle["text"],
                        "target_lang": request.target_lang,
                    },
                )
            )

        sentiment_task = None
        if request.enable_sentiment:
            sentiment_task = asyncio.create_task(
                call_service(
                    client,
                    SERVICES["sentiment"],
                    {
                        "session_id": request.session_id,
                        "speaker": subtitle["speaker"],
                        "text": subtitle["text"],
                    },
                )
            )

        if translation_task or sentiment_task:
            translation_res = (
                normalize_gateway_payload(await translation_task)
                if translation_task
                else None
            )
            sentiment_res = (
                normalize_gateway_payload(await sentiment_task)
                if sentiment_task
                else None
            )
            await websocket.send_json(
                {
                    "type": "analysis_result",
                    "data": {
                        "subtitle_id": subtitle["id"],
                        "speaker": subtitle["speaker"],
                        "timestamp": round(start_time, 3),
                        "translation": {
                            **translation_res,
                            "subtitle_id": subtitle["id"],
                        }
                        if translation_res
                        else None,
                        "sentiment": sentiment_res,
                    },
                }
            )

        if (
            request.enable_actions
            and state.action_window_start is not None
            and end_time - state.action_window_start >= 30.0
            and state.action_window_texts
        ):
            await flush_action_window(
                client=client,
                websocket=websocket,
                request=request,
                state=state,
                window_end=end_time,
            )

        if replay_delay > 0:
            try:
                await asyncio.wait_for(stop_requested.wait(), timeout=replay_delay)
            except asyncio.TimeoutError:
                pass

    await finalize_directory_pipeline(
        client=client,
        websocket=websocket,
        request=request,
        state=state,
    )


@app.websocket("/ws/pipeline/dir")
async def ws_pipeline_dir(websocket: WebSocket):
    await manager.connect(websocket)
    stop_requested = asyncio.Event()

    try:
        initial_payload = json.loads(await websocket.receive_text())
        request = build_directory_pipeline_request(initial_payload)

        async with httpx.AsyncClient() as client:
            replay_task = asyncio.create_task(
                run_directory_pipeline(
                    client=client,
                    websocket=websocket,
                    request=request,
                    stop_requested=stop_requested,
                )
            )
            control_task = asyncio.create_task(websocket.receive_text())

            while True:
                done, _ = await asyncio.wait(
                    {replay_task, control_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if replay_task in done:
                    if not control_task.done():
                        control_task.cancel()
                    await replay_task
                    break

                if control_task in done:
                    control_message = json.loads(control_task.result())
                    if control_message.get("type") == "end_meeting":
                        stop_requested.set()

                    if replay_task.done():
                        break

                    control_task = asyncio.create_task(websocket.receive_text())
    except WebSocketDisconnect:
        stop_requested.set()
        print("[Gateway] Directory pipeline disconnected")
    except Exception as error:
        try:
            await websocket.send_json({"type": "error", "message": str(error)})
        except Exception:
            pass
    finally:
        manager.disconnect(websocket)


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Gateway is running"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
