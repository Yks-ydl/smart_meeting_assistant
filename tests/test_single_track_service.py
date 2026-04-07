from __future__ import annotations

import unittest

from m1_speech.service import SingleTrackSpeechService
from m1_speech.utils.config import PipelineConfig
from m1_speech.utils.schemas import TranscriptSegment


class SingleTrackSpeechServiceTest(unittest.TestCase):
    """测试单轨服务层的响应组织逻辑。"""

    def test_build_response_contains_compatible_and_rich_fields(self) -> None:
        segments = [
            TranscriptSegment(
                text="hello",
                start_time=1.0,
                end_time=2.0,
                speaker_label="Orangezhi",
                confidence=0.8,
                source_channel="audioOrangezhi11999480170",
                language="en",
                corrected_text="Hello.",
            ),
            TranscriptSegment(
                text="world",
                start_time=2.0,
                end_time=3.0,
                speaker_label="Orangezhi",
                confidence=0.6,
                source_channel="audioOrangezhi11999480170",
                language="en",
                corrected_text="World.",
            ),
        ]

        payload = SingleTrackSpeechService._build_response(
            session_id="meeting_001",
            speaker_label="Orangezhi",
            source_channel="audioOrangezhi11999480170",
            segments=segments,
        )

        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["speaker"], "Orangezhi")
        self.assertEqual(payload["language"], "en")
        self.assertEqual(payload["start_time"], 1.0)
        self.assertEqual(payload["end_time"], 3.0)
        self.assertEqual(len(payload["segments"]), 2)
        self.assertEqual(payload["corrected_text"], "Hello. World.")

    def test_resolve_speaker_prefers_speaker_hint(self) -> None:
        service = SingleTrackSpeechService(PipelineConfig())
        source = type(
            "Source",
            (),
            {
                "speaker_hint": "ManualSpeaker",
                "source_id": "audioOrangezhi11999480170",
            },
        )()

        self.assertEqual(service._resolve_speaker_label(source), "ManualSpeaker")


if __name__ == "__main__":
    unittest.main()

