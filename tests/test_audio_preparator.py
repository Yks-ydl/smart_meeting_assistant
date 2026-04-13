from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from m1_speech.io.audio_preparator import AudioPreparationManager
from m1_speech.utils.config import AudioPrepConfig


class AudioPreparationManagerTest(unittest.TestCase):
    """测试原始音频准备层。"""

    def test_prepare_directory_fails_when_no_raw_audio_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = AudioPreparationManager(AudioPrepConfig(raw_dir=temp_dir))

            with self.assertRaises(FileNotFoundError):
                manager.prepare_directory()

    def test_build_output_path_maps_m4a_to_wav(self) -> None:
        raw_path = Path("audio/audioOrangezhi11999480170.m4a")
        converted_dir = Path("audio/converted")

        output_path = AudioPreparationManager.build_output_path(raw_path, converted_dir)

        self.assertEqual(output_path, Path("audio/converted/audioOrangezhi11999480170.wav"))


if __name__ == "__main__":
    unittest.main()
