from __future__ import annotations

import math

import torch

from m1_speech.utils.config import VADConfig


class VADProcessor:
    """一个轻量级占位 VAD 模块，只做首尾静音裁剪。"""

    def __init__(self, config: VADConfig) -> None:
        self.config = config

    def preprocess(self, waveform: torch.Tensor, sample_rate: int) -> tuple[torch.Tensor, float]:
        """返回裁剪后的波形，以及相对于原音频的时间偏移。"""

        if not self.config.enabled:
            return waveform, 0.0

        mono_waveform = waveform.squeeze(0)
        if mono_waveform.numel() == 0:
            return waveform, 0.0

        frame_size = max(1, int(sample_rate * self.config.frame_ms / 1000))
        min_frames = max(1, math.ceil(self.config.min_speech_ms / self.config.frame_ms))
        padding_frames = max(0, math.ceil(self.config.padding_ms / self.config.frame_ms))

        total_samples = mono_waveform.numel()
        frame_count = math.ceil(total_samples / frame_size)
        energies = []

        for frame_index in range(frame_count):
            start = frame_index * frame_size
            end = min(total_samples, start + frame_size)
            frame = mono_waveform[start:end]
            energy = float(frame.abs().mean().item()) if frame.numel() else 0.0
            energies.append(energy)

        active_indices = [idx for idx, energy in enumerate(energies) if energy >= self.config.energy_threshold]

        # 若检测不到清晰语音，则保留原波形，避免误裁剪。
        if len(active_indices) < min_frames:
            return waveform, 0.0

        start_frame = max(0, active_indices[0] - padding_frames)
        end_frame = min(frame_count - 1, active_indices[-1] + padding_frames)

        start_sample = start_frame * frame_size
        end_sample = min(total_samples, (end_frame + 1) * frame_size)
        trimmed = mono_waveform[start_sample:end_sample].unsqueeze(0)
        offset_seconds = start_sample / sample_rate

        return trimmed, offset_seconds

