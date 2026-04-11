from __future__ import annotations

import unittest

from m1_speech.pipeline.merger import TranscriptMerger
from m1_speech.utils.schemas import TranscriptSegment


class TranscriptMergerTest(unittest.TestCase):
    """测试 transcript 合并逻辑。"""

    def test_merge_orders_segments_by_start_time(self) -> None:
        merger = TranscriptMerger()

        later_segment = TranscriptSegment(
            text="second",
            start_time=3.0,
            end_time=4.0,
            speaker_label="Speaker_B",
            confidence=0.8,
            source_channel="channel_2",
            language="en",
            corrected_text=None,
        )
        earlier_segment = TranscriptSegment(
            text="first",
            start_time=1.0,
            end_time=2.0,
            speaker_label="Speaker_A",
            confidence=0.9,
            source_channel="channel_1",
            language="en",
            corrected_text=None,
        )

        merged = merger.merge([[later_segment], [earlier_segment]])

        self.assertEqual([segment.text for segment in merged], ["first", "second"])


if __name__ == "__main__":
    unittest.main()

