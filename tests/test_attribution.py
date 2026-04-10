from __future__ import annotations

from pathlib import Path
import unittest

from m1_speech.pipeline.attribution import ChannelSpeakerAttributor
from m1_speech.utils.config import SpeakerConfig
from m1_speech.utils.schemas import AudioSource


class ChannelSpeakerAttributorTest(unittest.TestCase):
    """测试 speaker 名字提取逻辑。"""

    def _build_attributor(self) -> ChannelSpeakerAttributor:
        return ChannelSpeakerAttributor(
            SpeakerConfig(
                label_mode="regex_name",
                name_pattern=r"^audio([A-Za-z]+?)(\d+)?$",
                fallback_mode="source_id",
            )
        )

    def test_extracts_name_from_first_audio_file(self) -> None:
        labels = self._build_attributor().assign_labels(
            [AudioSource(path=Path("audio/audioOrangezhi11999480170.wav"), source_id="audioOrangezhi11999480170")]
        )

        self.assertEqual(labels["audioOrangezhi11999480170"], "Orangezhi")

    def test_extracts_name_from_second_audio_file(self) -> None:
        labels = self._build_attributor().assign_labels(
            [AudioSource(path=Path("audio/audioYANGKaisen21999480170.wav"), source_id="audioYANGKaisen21999480170")]
        )

        self.assertEqual(labels["audioYANGKaisen21999480170"], "YANGKaisen")

    def test_falls_back_to_source_id_when_regex_does_not_match(self) -> None:
        labels = self._build_attributor().assign_labels(
            [AudioSource(path=Path("audio/random_meeting.wav"), source_id="random_meeting")]
        )

        self.assertEqual(labels["random_meeting"], "random_meeting")


if __name__ == "__main__":
    unittest.main()

