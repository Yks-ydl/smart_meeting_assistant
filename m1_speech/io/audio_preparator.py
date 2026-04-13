from __future__ import annotations

import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np

from m1_speech.utils.config import AudioPrepConfig


class AudioPreparationManager:
    """将原始会议音频转换为主流程使用的标准 WAV。"""

    def __init__(self, config: AudioPrepConfig) -> None:
        self.config = config

    def prepare_directory(
        self,
        raw_dir: str | Path | None = None,
        converted_dir: str | Path | None = None,
    ) -> list[Path]:
        """批量将原始音频转换为 16kHz 单声道 WAV。"""

        input_dir = Path(raw_dir or self.config.raw_dir)
        output_dir = Path(converted_dir or self.config.converted_dir)

        if not input_dir.exists():
            raise FileNotFoundError(f"Raw audio directory does not exist: {input_dir}")

        raw_files = sorted(input_dir.glob(self.config.raw_pattern))
        if not raw_files:
            raise FileNotFoundError(
                f"No raw audio files found in {input_dir} with pattern {self.config.raw_pattern}"
            )

        output_dir.mkdir(parents=True, exist_ok=True)
        prepared_files: list[Path] = []

        for raw_path in raw_files:
            output_path = self.build_output_path(raw_path, output_dir)
            self.prepare_file(raw_path, output_path)
            prepared_files.append(output_path)

        return prepared_files

    def prepare_file(self, raw_path: str | Path, output_path: str | Path) -> Path:
        """将单个文件转换为标准 WAV。"""

        source = Path(raw_path)
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        if self._can_use_torchaudio():
            self._prepare_with_torchaudio(source, target)
        elif self._can_use_librosa():
            self._prepare_with_librosa(source, target)
        elif self._can_use_afconvert():
            self._prepare_with_afconvert(source, target)
        else:
            raise RuntimeError(
                "Audio preparation requires torchaudio, librosa, or the macOS afconvert tool."
            )

        return target

    @staticmethod
    def build_output_path(raw_path: str | Path, converted_dir: str | Path) -> Path:
        """根据原始文件名生成对应的 WAV 输出路径。"""

        source = Path(raw_path)
        output_dir = Path(converted_dir)
        return output_dir / f"{source.stem}.wav"

    @staticmethod
    def _can_use_librosa() -> bool:
        try:
            import librosa  # noqa: F401
        except ImportError:
            return False
        return True

    @staticmethod
    def _can_use_torchaudio() -> bool:
        try:
            import torchaudio  # noqa: F401
            import torchcodec  # noqa: F401
        except (ImportError, OSError) as e:
            print(f"[AudioPreparator] Warning: Cannot use torchaudio/torchcodec ({e}). Falling back to librosa.")
            return False
        return True

    @staticmethod
    def _can_use_afconvert() -> bool:
        return shutil.which("afconvert") is not None

    def _prepare_with_librosa(self, source: Path, target: Path) -> None:
        """优先使用 librosa 读取原始文件，再写出标准 WAV。"""

        import librosa

        waveform, _ = librosa.load(
            source,
            sr=self.config.target_sample_rate,
            mono=self.config.mono,
        )
        self._write_pcm_wav(target, waveform, self.config.target_sample_rate)

    def _prepare_with_torchaudio(self, source: Path, target: Path) -> None:
        """优先使用 torchaudio + torchcodec 读取原始文件。"""

        import torchaudio

        waveform, sample_rate = torchaudio.load(str(source))
        if waveform.dim() == 2 and waveform.size(0) > 1 and self.config.mono:
            waveform = waveform.mean(dim=0, keepdim=True)

        if sample_rate != self.config.target_sample_rate:
            resampler = torchaudio.transforms.Resample(
                orig_freq=sample_rate,
                new_freq=self.config.target_sample_rate,
            )
            waveform = resampler(waveform)

        self._write_pcm_wav(
            target,
            waveform.squeeze(0).detach().cpu().numpy(),
            self.config.target_sample_rate,
        )

    def _prepare_with_afconvert(self, source: Path, target: Path) -> None:
        """在 macOS 环境下回退使用 afconvert 生成标准 WAV。"""

        channels = "1" if self.config.mono else "2"
        command = [
            "afconvert",
            str(source),
            "-o",
            str(target),
            "-f",
            "WAVE",
            "-d",
            f"LEI16@{self.config.target_sample_rate}",
            "-c",
            channels,
        ]
        subprocess.run(command, check=True)

    @staticmethod
    def _write_pcm_wav(target: Path, waveform: np.ndarray, sample_rate: int) -> None:
        """将浮点波形写出为 16-bit PCM WAV。"""

        clipped = np.clip(np.asarray(waveform, dtype=np.float32), -1.0, 1.0)
        pcm = (clipped * 32767.0).astype(np.int16)

        with wave.open(str(target), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(sample_rate)
            handle.writeframes(pcm.tobytes())
