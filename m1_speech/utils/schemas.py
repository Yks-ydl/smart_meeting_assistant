from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class AudioSource:
    """表示一个独立参会人的音频来源。"""

    path: Path
    source_id: str
    speaker_hint: str | None = None


@dataclass(slots=True)
class TranscriptSegment:
    """统一的转写片段数据结构。"""

    text: str
    start_time: float
    end_time: float
    speaker_label: str
    confidence: float | None
    source_channel: str
    language: str | None
    corrected_text: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """将数据结构转换为便于 JSON 导出的字典。"""

        return asdict(self)

