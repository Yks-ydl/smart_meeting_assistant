from __future__ import annotations

from itertools import chain

from m1_speech.utils.schemas import TranscriptSegment


class TranscriptMerger:
    """按时间戳合并多个独立音轨的转写结果。"""

    def merge(self, transcript_groups: list[list[TranscriptSegment]]) -> list[TranscriptSegment]:
        """将多路 transcript 展平成单一路会议记录。"""

        merged = list(chain.from_iterable(transcript_groups))
        merged.sort(key=lambda item: (item.start_time, item.end_time, item.speaker_label))
        return merged

