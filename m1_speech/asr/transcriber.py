from __future__ import annotations

import math
from typing import Any

import numpy as np
import torch

from m1_speech.utils.config import ASRConfig
from m1_speech.utils.schemas import TranscriptSegment


class ASRTranscriber:
    """对单个独立音轨执行 faster-whisper 转写。"""

    def __init__(self, config: ASRConfig) -> None:
        self.config = config
        self._model: Any | None = None

    def transcribe(
        self,
        waveform: torch.Tensor,
        sample_rate: int,
        source_channel: str,
        speaker_label: str,
        start_offset: float = 0.0,
        language: str | None = None,
    ) -> list[TranscriptSegment]:
        """将单个音轨转换为统一 transcript 片段列表。"""

        if sample_rate != self.config.sample_rate:
            raise ValueError(
                f"Expected sample rate {self.config.sample_rate}, but received {sample_rate}. "
                "Please resample audio before ASR."
            )

        model = self._get_model()
        audio = waveform.squeeze(0).detach().cpu().numpy().astype(np.float32)
        resolved_language = language or self.config.language

        # 对每条独立音轨先做语言检测，再执行正式转写。
        if resolved_language is None and self.config.detect_language_first:
            detected_language, _, _ = model.detect_language(
                audio=audio,
                vad_filter=self.config.vad_filter,
                language_detection_segments=self.config.language_detection_segments,
                language_detection_threshold=self.config.language_detection_threshold,
            )
            resolved_language = detected_language

        segments, info = model.transcribe(
            audio=audio,
            language=resolved_language,
            beam_size=self.config.beam_size,
            multilingual=self.config.multilingual,
            vad_filter=self.config.vad_filter,
            word_timestamps=self.config.word_timestamps,
        )

        detected_language = getattr(info, "language", resolved_language)
        results: list[TranscriptSegment] = []

        for segment in segments:
            raw_text = segment.text.strip()
            if not raw_text:
                continue

            results.append(
                TranscriptSegment(
                    text=raw_text,
                    start_time=float(segment.start) + start_offset,
                    end_time=float(segment.end) + start_offset,
                    speaker_label=speaker_label,
                    confidence=self._estimate_confidence(getattr(segment, "avg_logprob", None)),
                    source_channel=source_channel,
                    language=detected_language,
                    corrected_text=None,
                )
            )

        return results

    def _get_model(self) -> Any:
        """懒加载 faster-whisper 模型，降低初始化开销。"""

        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as error:
                raise ImportError(
                    "faster-whisper is required for ASR. Please install dependencies from requirements.txt."
                ) from error

            self._model = WhisperModel(
                model_size_or_path=self.config.model_size,
                device=self.config.device,
                compute_type=self.config.compute_type,
            )

        return self._model

    @staticmethod
    def _estimate_confidence(avg_logprob: float | None) -> float | None:
        """将 avg_logprob 转成一个便于展示的近似置信度分数。"""

        if avg_logprob is None:
            return None

        return round(1.0 / (1.0 + math.exp(-avg_logprob)), 4)
