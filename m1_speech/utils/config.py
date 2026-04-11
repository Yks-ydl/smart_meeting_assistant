from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ASRConfig:
    """ASR 模型相关配置。"""

    model_size: str = "small"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str | None = None
    detect_language_first: bool = True
    multilingual: bool = True
    language_detection_segments: int = 2
    language_detection_threshold: float = 0.5
    beam_size: int = 5
    vad_filter: bool = False
    word_timestamps: bool = False
    sample_rate: int = 16000


@dataclass(slots=True)
class VADConfig:
    """VAD 预处理相关配置。"""

    enabled: bool = True
    energy_threshold: float = 0.01
    frame_ms: int = 30
    min_speech_ms: int = 300
    padding_ms: int = 200


@dataclass(slots=True)
class SpeakerConfig:
    """说话人标签映射配置。"""

    label_mode: str = "source_id"
    anonymous_prefix: str = "Speaker"
    name_pattern: str = r"^audio([A-Za-z]+?)(\d+)?$"
    fallback_mode: str = "source_id"


@dataclass(slots=True)
class PostProcessConfig:
    """文本后处理配置。"""

    enabled: bool = True
    remove_fillers: bool = True
    capitalize: bool = True
    restore_punctuation: bool = True


@dataclass(slots=True)
class InputConfig:
    """输入管理配置。"""

    glob_pattern: str = "*.wav"
    recursive: bool = False


@dataclass(slots=True)
class AudioPrepConfig:
    """原始音频转换配置。"""

    enabled: bool = True
    raw_dir: str = "audio"
    converted_dir: str = "audio/converted"
    raw_pattern: str = "*.m4a"
    target_sample_rate: int = 16000
    mono: bool = True


@dataclass(slots=True)
class OutputConfig:
    """输出目录配置。"""

    output_dir: str = "outputs"
    json_name: str = "merged_transcript.json"
    txt_name: str = "merged_transcript.txt"


@dataclass(slots=True)
class PipelineConfig:
    """语音模块总配置。"""

    asr: ASRConfig = field(default_factory=ASRConfig)
    vad: VADConfig = field(default_factory=VADConfig)
    speaker: SpeakerConfig = field(default_factory=SpeakerConfig)
    postprocess: PostProcessConfig = field(default_factory=PostProcessConfig)
    input: InputConfig = field(default_factory=InputConfig)
    audio_prep: AudioPrepConfig = field(default_factory=AudioPrepConfig)
    output: OutputConfig = field(default_factory=OutputConfig)


class ConfigLoader:
    """负责从 JSON 文件加载配置。"""

    @staticmethod
    def load(path: str | Path) -> PipelineConfig:
        """从 JSON 文件中读取配置并构建配置对象。"""

        config_path = Path(path)
        with config_path.open("r", encoding="utf-8") as handle:
            raw_config: dict[str, Any] = json.load(handle)

        return PipelineConfig(
            asr=ASRConfig(**raw_config.get("asr", {})),
            vad=VADConfig(**raw_config.get("vad", {})),
            speaker=SpeakerConfig(**raw_config.get("speaker", {})),
            postprocess=PostProcessConfig(**raw_config.get("postprocess", {})),
            input=InputConfig(**raw_config.get("input", {})),
            audio_prep=AudioPrepConfig(**raw_config.get("audio_prep", {})),
            output=OutputConfig(**raw_config.get("output", {})),
        )
