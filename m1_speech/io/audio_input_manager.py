from __future__ import annotations

import wave
from pathlib import Path
from typing import Iterable

import numpy as np
import torch

from m1_speech.utils.config import InputConfig
from m1_speech.utils.schemas import AudioSource


class AudioInputManager:
    """管理离线音频输入，并为未来实时输入预留接口。"""

    def __init__(self, config: InputConfig, target_sample_rate: int = 16000) -> None:
        self.config = config
        self.target_sample_rate = target_sample_rate

    def discover_audio_sources(self, input_dir: str | Path) -> list[AudioSource]:
        """扫描输入目录，收集多个独立音轨文件。"""

        input_path = Path(input_dir)
        if not input_path.exists():
            raise FileNotFoundError(f"Input directory does not exist: {input_path}")

        if self.config.recursive:
            files = sorted(input_path.rglob(self.config.glob_pattern))
        else:
            files = sorted(input_path.glob(self.config.glob_pattern))

        sources: list[AudioSource] = []
        for file_path in files:
            if file_path.is_file():
                source_id = self._extract_source_id(file_path)
                sources.append(AudioSource(path=file_path, source_id=source_id, speaker_hint=source_id))

        if not sources:
            raise FileNotFoundError(
                f"No audio files found in {input_path} with pattern {self.config.glob_pattern}"
            )

        return sources

    def load_waveform(self, source: AudioSource) -> tuple[torch.Tensor, int]:
        """读取音频，并统一重采样到目标采样率。"""

        waveform, sample_rate = self._load_with_available_backend(source.path)
        mono_waveform = waveform.squeeze(0).detach().cpu().numpy()
        if mono_waveform.size > 0 and not np.allclose(mono_waveform, 0.0):
            normalized = self._normalize_audio(mono_waveform)
            waveform = torch.from_numpy(normalized).unsqueeze(0).to(dtype=torch.float32)

        return waveform, sample_rate

    def stream_input_placeholder(self) -> Iterable[AudioSource]:
        """为未来实时流式输入预留扩展入口。"""

        raise NotImplementedError("Streaming input is reserved for future versions.")

    @staticmethod
    def _extract_source_id(file_path: Path) -> str:
        """从文件名中提取 channel_id 或 user_id。"""

        return file_path.stem

    def _load_with_available_backend(self, path: Path) -> tuple[torch.Tensor, int]:
        """优先使用 torchaudio，缺失时回退到标准库 WAV 读取。"""

        try:
            import torchaudio
        except ImportError:
            torchaudio = None

        if torchaudio is not None:
            try:
                waveform, sample_rate = torchaudio.load(str(path))
                if waveform.dim() == 2 and waveform.size(0) > 1:
                    waveform = waveform.mean(dim=0, keepdim=True)

                if sample_rate != self.target_sample_rate:
                    resampler = torchaudio.transforms.Resample(
                        orig_freq=sample_rate,
                        new_freq=self.target_sample_rate,
                    )
                    waveform = resampler(waveform)
                    sample_rate = self.target_sample_rate

                return waveform.to(dtype=torch.float32), sample_rate
            except Exception:
                if path.suffix.lower() != ".wav":
                    raise

        if path.suffix.lower() != ".wav":
            raise RuntimeError(
                "torchaudio is not installed, so only prepared WAV files can be loaded in the current environment."
            )

        with wave.open(str(path), "rb") as handle:
            sample_rate = handle.getframerate()
            sample_width = handle.getsampwidth()
            num_channels = handle.getnchannels()
            frame_count = handle.getnframes()
            pcm_bytes = handle.readframes(frame_count)

        dtype_map = {
            1: np.uint8,
            2: np.int16,
            4: np.int32,
        }
        dtype = dtype_map.get(sample_width)
        if dtype is None:
            raise ValueError(f"Unsupported WAV sample width: {sample_width}")

        samples = np.frombuffer(pcm_bytes, dtype=dtype)
        if sample_width == 1:
            samples = (samples.astype(np.float32) - 128.0) / 128.0
        elif sample_width == 2:
            samples = samples.astype(np.float32) / 32768.0
        else:
            samples = samples.astype(np.float32) / 2147483648.0

        if num_channels > 1:
            samples = samples.reshape(-1, num_channels).mean(axis=1)

        waveform = torch.from_numpy(samples.astype(np.float32)).unsqueeze(0)
        if sample_rate != self.target_sample_rate:
            raise ValueError(
                f"Prepared WAV must use sample rate {self.target_sample_rate}, but received {sample_rate} from {path}."
            )

        return waveform, sample_rate

    @staticmethod
    def _normalize_audio(audio: np.ndarray) -> np.ndarray:
        """对音频做轻量归一化，缺失 librosa 时使用 numpy 回退。"""

        try:
            import librosa
        except ImportError:
            peak = float(np.max(np.abs(audio))) if audio.size else 0.0
            if peak <= 0.0:
                return audio.astype(np.float32)
            return (audio / peak).astype(np.float32)

        return librosa.util.normalize(audio).astype(np.float32)
