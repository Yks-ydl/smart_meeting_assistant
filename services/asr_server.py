from __future__ import annotations

import os
import sys

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

# 解决 Windows 环境下常见的 OMP 冲突报错
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from m1_speech.service import SingleTrackSpeechService
from m1_speech.utils.config import ASRConfig, InputConfig, PipelineConfig, PostProcessConfig, SpeakerConfig, VADConfig

app = FastAPI(title="M1 - ASR & Speech Processing Service")


def build_pipeline_config() -> PipelineConfig:
    """构建 M1 服务默认配置。"""

    model_size = os.getenv("M1_MODEL_SIZE_OR_PATH", "small")
    return PipelineConfig(
        asr=ASRConfig(
            model_size=model_size,
            device=os.getenv("M1_DEVICE", "cpu"),
            compute_type=os.getenv("M1_COMPUTE_TYPE", "int8"),
            language=None,
            detect_language_first=True,
            multilingual=True,
            beam_size=int(os.getenv("M1_BEAM_SIZE", "5")),
            vad_filter=True,
            sample_rate=int(os.getenv("M1_SAMPLE_RATE", "16000")),
        ),
        vad=VADConfig(
            enabled=True,
            energy_threshold=float(os.getenv("M1_VAD_ENERGY_THRESHOLD", "0.01")),
        ),
        speaker=SpeakerConfig(
            label_mode=os.getenv("M1_SPEAKER_LABEL_MODE", "regex_name"),
            name_pattern=os.getenv("M1_SPEAKER_NAME_PATTERN", r"^audio([A-Za-z]+?)(\d+)?$"),
            fallback_mode=os.getenv("M1_SPEAKER_FALLBACK_MODE", "source_id"),
        ),
        postprocess=PostProcessConfig(enabled=True),
        input=InputConfig(glob_pattern="*.wav", recursive=False),
    )


speech_service = SingleTrackSpeechService(build_pipeline_config())


class AudioData(BaseModel):
    """M1 单轨处理接口请求模型。"""

    audio_base64: str
    session_id: str
    speaker_hint: str | None = None
    source_channel: str | None = None
    chunk_start_time: float = 0.0
    language_hint: str | None = None
    audio_format: str = "webm"


@app.post("/api/v1/asr/transcribe")
async def transcribe(audio: AudioData):
    """
    接收单条独立音轨，先检测语言，再执行 ASR，并返回统一 transcript 结构。
    """

    if not audio.audio_base64:
        return {
            "status": "error",
            "session_id": audio.session_id,
            "message": "audio_base64 is required",
        }

    try:
        audio_bytes = speech_service.decode_base64_audio(audio.audio_base64)
        return speech_service.transcribe_bytes(
            audio_bytes=audio_bytes,
            session_id=audio.session_id,
            suffix=audio.audio_format,
            speaker_hint=audio.speaker_hint,
            source_channel=audio.source_channel,
            chunk_start_time=audio.chunk_start_time,
            language_hint=audio.language_hint,
        )
    except Exception as error:
        print(f"[M1] ASR processing failed: {error}")
        return {
            "status": "error",
            "session_id": audio.session_id,
            "message": str(error),
            "speaker": audio.speaker_hint or audio.source_channel or "Unknown",
        }


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "M1 - ASR & Speech Processing Service"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
