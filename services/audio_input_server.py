from __future__ import annotations

from base64 import b64encode
import os
from pathlib import Path
import sys
import tempfile
import threading
from typing import Dict, List

import httpx
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from m1_speech.io.audio_preparator import AudioPreparationManager
from m1_speech.pipeline.attribution import ChannelSpeakerAttributor
from m1_speech.pipeline.merger import TranscriptMerger
from m1_speech.utils.config import AudioPrepConfig, SpeakerConfig
from m1_speech.utils.schemas import AudioSource

app = FastAPI(title="M6 - Audio Input Service")

ASR_SERVICE_URL = os.getenv("ASR_SERVICE_URL", "http://127.0.0.1:8001/api/v1/asr/transcribe")
# M1 首次调用需加载 Whisper 模型(~484MB)，加上 CPU 推理长音频，单轨需足够超时
ASR_PER_TRACK_TIMEOUT = float(os.getenv("M6_ASR_TIMEOUT", "300"))
DEFAULT_AUDIO_GLOB_PATTERN = "*"
SUPPORTED_AUDIO_SUFFIXES = {".m4a", ".wav", ".mp3", ".flac", ".aac", ".ogg", ".webm"}


class AudioServiceState:
    """本地目录处理模式下的全局状态。"""

    def __init__(self) -> None:
        self.is_processing = False
        self.current_mode = None
        self.current_session_id = None
        self.input_dir = None
        self.track_info: List[dict] = []
        self.track_results: List[dict] = []
        self.merged_transcript: List[dict] = []
        self.full_text = ""
        self.errors: List[dict] = []
        self.stop_event = threading.Event()


state = AudioServiceState()


class ProcessDirectoryRequest(BaseModel):
    session_id: str
    input_dir: str
    glob_pattern: str = DEFAULT_AUDIO_GLOB_PATTERN
    recursive: bool = False


def build_speaker_attributor() -> ChannelSpeakerAttributor:
    """构建与当前课程项目一致的 speaker 标注规则。"""

    return ChannelSpeakerAttributor(
        SpeakerConfig(
            label_mode=os.getenv("M1_SPEAKER_LABEL_MODE", "regex_name"),
            name_pattern=os.getenv("M1_SPEAKER_NAME_PATTERN", r"^audio([A-Za-z]+?)(\d+)?$"),
            fallback_mode=os.getenv("M1_SPEAKER_FALLBACK_MODE", "source_id"),
        )
    )


def build_audio_preparator(glob_pattern: str) -> AudioPreparationManager:
    """构建原始音频准备器。"""

    return AudioPreparationManager(
        AudioPrepConfig(
            enabled=True,
            raw_pattern=glob_pattern,
            target_sample_rate=int(os.getenv("M1_SAMPLE_RATE", "16000")),
            mono=True,
        )
    )


def discover_raw_sources(input_dir: str | Path, glob_pattern: str, recursive: bool) -> list[AudioSource]:
    """扫描目录中的独立音轨文件，默认同时支持常见会议音频格式。"""

    root = Path(input_dir)
    if not root.exists():
        raise FileNotFoundError(f"Input directory does not exist: {root}")

    paths = sorted(root.rglob(glob_pattern) if recursive else root.glob(glob_pattern))
    files = [
        path
        for path in paths
        if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_SUFFIXES
    ]
    if not files:
        supported = ", ".join(sorted(SUPPORTED_AUDIO_SUFFIXES))
        raise FileNotFoundError(
            f"No audio files found in {root} with pattern {glob_pattern}. Supported suffixes: {supported}"
        )

    return [AudioSource(path=path, source_id=path.stem, speaker_hint=None) for path in files]


async def send_track_to_asr(
    client: httpx.AsyncClient,
    wav_path: Path,
    session_id: str,
    speaker_label: str,
    source_channel: str,
) -> dict:
    """将单轨标准 WAV 发送给 M1 服务。"""

    audio_base64 = b64encode(wav_path.read_bytes()).decode("utf-8")
    payload = {
        "audio_base64": audio_base64,
        "session_id": session_id,
        "speaker_hint": speaker_label,
        "source_channel": source_channel,
        "chunk_start_time": 0.0,
        "audio_format": "wav",
    }
    response = await client.post(ASR_SERVICE_URL, json=payload, timeout=ASR_PER_TRACK_TIMEOUT)
    return response.json()


def format_full_text(merged_transcript: list[dict]) -> str:
    """将 merged transcript 格式化为适合阅读的完整会议文本。"""

    lines = []
    for segment in merged_transcript:
        start = float(segment["start_time"])
        end = float(segment["end_time"])
        speaker = segment["speaker_label"]
        text = segment.get("corrected_text") or segment["text"]
        lines.append(f"[{start:07.2f}s - {end:07.2f}s] {speaker}: {text}")
    return "\n".join(lines)


@app.post("/api/v1/audio/process_directory")
async def process_directory(req: ProcessDirectoryRequest):
    """
    读取本地目录中的多个独立音轨文件，并输出统一会议 transcript。
    """

    if state.is_processing:
        return {
            "status": "error",
            "session_id": req.session_id,
            "message": "Another directory processing task is already running.",
        }

    state.is_processing = True
    state.current_mode = "independent_tracks_from_directory"
    state.current_session_id = req.session_id
    state.input_dir = req.input_dir
    state.track_info = []
    state.track_results = []
    state.merged_transcript = []
    state.full_text = ""
    state.errors = []

    try:
        raw_sources = discover_raw_sources(req.input_dir, req.glob_pattern, req.recursive)
        speaker_attributor = build_speaker_attributor()
        speaker_labels = speaker_attributor.assign_labels(raw_sources)

        with tempfile.TemporaryDirectory(prefix="m6_prepared_") as tmp_dir:
            preparator = build_audio_preparator(req.glob_pattern)

            async with httpx.AsyncClient() as client:
                for source in raw_sources:
                    source_channel = source.source_id
                    speaker_label = speaker_labels[source.source_id]
                    prepared_path = AudioPreparationManager.build_output_path(source.path, tmp_dir)

                    try:
                        preparator.prepare_file(source.path, prepared_path)
                        track_response = await send_track_to_asr(
                            client=client,
                            wav_path=prepared_path,
                            session_id=req.session_id,
                            speaker_label=speaker_label,
                            source_channel=source_channel,
                        )

                        if track_response.get("status") != "success":
                            raise RuntimeError(track_response.get("message", "Unknown ASR error"))

                        state.track_info.append(
                            {
                                "filename": source.path.name,
                                "source_channel": source_channel,
                                "speaker_label": speaker_label,
                                "detected_language": track_response.get("language"),
                            }
                        )
                        state.track_results.append(track_response)
                    except Exception as error:
                        state.errors.append(
                            {
                                "filename": source.path.name,
                                "source_channel": source_channel,
                                "message": str(error),
                            }
                        )

        merger = TranscriptMerger()
        transcript_groups = [result.get("segments", []) for result in state.track_results]
        merged_segments = merger.merge(
            [
                [
                    # 将 dict 还原为排序所需的字段结构
                    AudioSegmentAdapter(segment)
                    for segment in group
                ]
                for group in transcript_groups
            ]
        )
        state.merged_transcript = [segment.to_dict() for segment in merged_segments]
        state.full_text = format_full_text(state.merged_transcript)

        status = "partial_success" if state.errors else "success"
        return {
            "status": status,
            "session_id": req.session_id,
            "mode": state.current_mode,
            "input_dir": req.input_dir,
            "track_info": state.track_info,
            "track_results": state.track_results,
            "merged_transcript": state.merged_transcript,
            "full_text": state.full_text,
            "errors": state.errors,
        }
    except Exception as error:
        state.errors.append({"message": str(error)})
        return {
            "status": "error",
            "session_id": req.session_id,
            "mode": state.current_mode,
            "input_dir": req.input_dir,
            "message": str(error),
            "errors": state.errors,
        }
    finally:
        state.is_processing = False


@app.get("/api/v1/audio/status")
async def get_status():
    """查询当前目录处理任务的状态。"""

    return {
        "status": "success",
        "is_processing": state.is_processing,
        "current_mode": state.current_mode,
        "session_id": state.current_session_id,
        "input_dir": state.input_dir,
        "track_count": len(state.track_info),
        "result_count": len(state.track_results),
        "error_count": len(state.errors),
    }


@app.get("/api/v1/audio/tracks/{session_id}")
async def get_tracks(session_id: str):
    """获取指定会话最近一次目录处理结果。"""

    if state.current_session_id != session_id:
        return {
            "status": "error",
            "message": f"未找到会话 {session_id} 的结果",
        }

    return {
        "status": "success",
        "session_id": session_id,
        "mode": state.current_mode,
        "input_dir": state.input_dir,
        "track_info": state.track_info,
        "track_results": state.track_results,
        "merged_transcript": state.merged_transcript,
        "full_text": state.full_text,
        "errors": state.errors,
        "is_complete": not state.is_processing,
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "M6 - Audio Input",
        "is_processing": state.is_processing,
        "mode": state.current_mode,
    }


class AudioSegmentAdapter:
    """将 dict transcript 片段适配为 TranscriptMerger 所需对象。"""

    def __init__(self, payload: dict) -> None:
        self.text = payload["text"]
        self.start_time = float(payload["start_time"])
        self.end_time = float(payload["end_time"])
        self.speaker_label = payload["speaker_label"]
        self.confidence = payload.get("confidence")
        self.source_channel = payload["source_channel"]
        self.language = payload.get("language")
        self.corrected_text = payload.get("corrected_text")

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "speaker_label": self.speaker_label,
            "confidence": self.confidence,
            "source_channel": self.source_channel,
            "language": self.language,
            "corrected_text": self.corrected_text,
        }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
