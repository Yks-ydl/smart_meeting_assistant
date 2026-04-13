from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services.audio_input_server import (
    ProcessDirectoryRequest,
    discover_raw_sources,
    format_full_text,
)


class AudioInputServerHelpersTest(unittest.TestCase):
    """测试目录处理服务的辅助函数。"""

    def test_discover_raw_sources_reads_independent_m4a_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "audioOrangezhi11999480170.m4a").write_bytes(b"a")
            (root / "audioYANGKaisen21999480170.m4a").write_bytes(b"b")

            sources = discover_raw_sources(root, "*.m4a", recursive=False)

            self.assertEqual([source.source_id for source in sources], [
                "audioOrangezhi11999480170",
                "audioYANGKaisen21999480170",
            ])

    def test_discover_raw_sources_default_pattern_reads_wav_tracks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "audioOrangezhi11999480170.wav").write_bytes(b"a")
            (root / "audioYANGKaisen21999480170.wav").write_bytes(b"b")

            sources = discover_raw_sources(root, "*", recursive=False)

            self.assertEqual([source.source_id for source in sources], [
                "audioOrangezhi11999480170",
                "audioYANGKaisen21999480170",
            ])

    def test_process_directory_request_defaults_to_multi_format_pattern(self) -> None:
        request_model = ProcessDirectoryRequest(
            session_id="meeting_demo",
            input_dir="audio",
        )

        self.assertEqual(request_model.glob_pattern, "*")

    def test_format_full_text_uses_timestamped_lines(self) -> None:
        transcript = [
            {
                "text": "raw",
                "start_time": 2.1,
                "end_time": 5.8,
                "speaker_label": "Orangezhi",
                "confidence": 0.8,
                "source_channel": "audioOrangezhi11999480170",
                "language": "zh",
                "corrected_text": "对了，我试一下那个音轨。",
            }
        ]

        full_text = format_full_text(transcript)

        self.assertIn("Orangezhi", full_text)
        self.assertIn("对了，我试一下那个音轨。", full_text)
        self.assertIn("[0002.10s - 0005.80s]", full_text)


if __name__ == "__main__":
    unittest.main()
