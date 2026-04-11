from __future__ import annotations

import base64
import tempfile
from pathlib import Path

from m1_speech.asr.transcriber import ASRTranscriber
from m1_speech.asr.vad import VADProcessor
from m1_speech.io.audio_input_manager import AudioInputManager
from m1_speech.pipeline.attribution import ChannelSpeakerAttributor
from m1_speech.postprocess.text_postprocessor import TextPostProcessor
from m1_speech.utils.config import PipelineConfig
from m1_speech.utils.schemas import AudioSource, TranscriptSegment


class SingleTrackSpeechService:
    """将单轨音频处理流程封装为服务层，供 M1 / M6 复用。"""

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self.audio_input_manager = AudioInputManager(
            config=config.input,
            target_sample_rate=config.asr.sample_rate,
        )
        self.vad_processor = VADProcessor(config=config.vad)
        self.transcriber = ASRTranscriber(config=config.asr)
        self.speaker_attributor = ChannelSpeakerAttributor(config=config.speaker)
        self.text_postprocessor = TextPostProcessor(config=config.postprocess)

    def transcribe_file(
        self,
        audio_path: str | Path,
        session_id: str,
        speaker_hint: str | None = None,
        source_channel: str | None = None,
        chunk_start_time: float = 0.0,
        language_hint: str | None = None,
    ) -> dict:
        """处理单个音频文件并返回统一响应。"""

        path = Path(audio_path)
        resolved_source_channel = source_channel or path.stem
        source = AudioSource(
            path=path,
            source_id=resolved_source_channel,
            speaker_hint=speaker_hint,
        )

        waveform, sample_rate = self.audio_input_manager.load_waveform(source)
        processed_waveform, offset_seconds = self.vad_processor.preprocess(waveform, sample_rate)

        speaker_label = self._resolve_speaker_label(source)
        segments = self.transcriber.transcribe(
            waveform=processed_waveform,
            sample_rate=sample_rate,
            source_channel=resolved_source_channel,
            speaker_label=speaker_label,
            start_offset=chunk_start_time + offset_seconds,
            language=language_hint,
        )
        processed_segments = self.text_postprocessor.process_segments(segments)
        return self._build_response(session_id, speaker_label, resolved_source_channel, processed_segments)

    def transcribe_bytes(
        self,
        audio_bytes: bytes,
        session_id: str,
        suffix: str = ".wav",
        speaker_hint: str | None = None,
        source_channel: str | None = None,
        chunk_start_time: float = 0.0,
        language_hint: str | None = None,
    ) -> dict:
        """处理单轨字节流，内部写入临时文件后复用文件处理逻辑。"""

        normalized_suffix = suffix if suffix.startswith(".") else f".{suffix}"
        with tempfile.NamedTemporaryFile(delete=False, suffix=normalized_suffix) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = Path(tmp_file.name)

        try:
            return self.transcribe_file(
                audio_path=tmp_path,
                session_id=session_id,
                speaker_hint=speaker_hint,
                source_channel=source_channel,
                chunk_start_time=chunk_start_time,
                language_hint=language_hint,
            )
        finally:
            tmp_path.unlink(missing_ok=True)

    @staticmethod
    def decode_base64_audio(audio_base64: str) -> bytes:
        """解码 Base64 音频内容。"""

        return base64.b64decode(audio_base64)

    def _resolve_speaker_label(self, source: AudioSource) -> str:
        """优先使用明确 speaker_hint，否则按配置规则从 source_id 生成 speaker。"""

        if source.speaker_hint:
            return source.speaker_hint
        labels = self.speaker_attributor.assign_labels([source])
        return labels[source.source_id]

    @staticmethod
    def _build_response(
        session_id: str,
        speaker_label: str,
        source_channel: str,
        segments: list[TranscriptSegment],
    ) -> dict:
        """将 segment 列表整理为服务响应。"""

        joined_text = " ".join(segment.text for segment in segments).strip()
        joined_corrected_text = " ".join(
            (segment.corrected_text or segment.text).strip() for segment in segments
        ).strip()

        confidence_values = [segment.confidence for segment in segments if segment.confidence is not None]
        confidence = round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else None
        start_time = segments[0].start_time if segments else 0.0
        end_time = segments[-1].end_time if segments else 0.0
        language = segments[0].language if segments else None

        return {
            "status": "success",
            "session_id": session_id,
            "speaker": speaker_label,
            "text": joined_text,
            "language": language,
            "source_channel": source_channel,
            "confidence": confidence,
            "corrected_text": joined_corrected_text,
            "start_time": start_time,
            "end_time": end_time,
            "segments": [segment.to_dict() for segment in segments],
        }
