from __future__ import annotations

import json
from pathlib import Path

from m1_speech.utils.schemas import TranscriptSegment


class TranscriptExporter:
    """负责导出 JSON 和 TXT 两种会议转写结果。"""

    @staticmethod
    def export_json(segments: list[TranscriptSegment], output_path: str | Path) -> Path:
        """导出标准 JSON 结果。"""

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = [segment.to_dict() for segment in segments]
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

        return path

    @staticmethod
    def export_txt(segments: list[TranscriptSegment], output_path: str | Path) -> Path:
        """导出适合展示的纯文本会议记录。"""

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = []
        for segment in segments:
            display_text = segment.corrected_text or segment.text
            timestamp = f"[{segment.start_time:07.2f}s - {segment.end_time:07.2f}s]"
            lines.append(f"{timestamp} {segment.speaker_label}: {display_text}")

        with path.open("w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))

        return path

