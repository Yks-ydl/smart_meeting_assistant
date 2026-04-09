from __future__ import annotations

import unittest

from m1_speech.postprocess.text_postprocessor import TextPostProcessor
from m1_speech.utils.config import PostProcessConfig
from m1_speech.utils.schemas import TranscriptSegment


class TextPostProcessorTest(unittest.TestCase):
    """测试规则式 BTS 后处理模块。"""

    def test_process_text_removes_fillers_and_restores_punctuation(self) -> None:
        processor = TextPostProcessor(PostProcessConfig())

        result = processor.process_text("um hello team", language="en")

        self.assertEqual(result, "Hello team.")

    def test_process_segments_writes_corrected_text(self) -> None:
        processor = TextPostProcessor(PostProcessConfig())
        segments = [
            TranscriptSegment(
                text="uh thanks for joining",
                start_time=0.0,
                end_time=1.0,
                speaker_label="Speaker_A",
                confidence=0.8,
                source_channel="channel_1",
                language="en",
                corrected_text=None,
            )
        ]

        updated = processor.process_segments(segments)

        self.assertEqual(updated[0].corrected_text, "Thanks for joining.")


if __name__ == "__main__":
    unittest.main()

