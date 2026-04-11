from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.vcsum_data import format_transcript, get_participants, load_vcsum_data


class VCSumDataLoaderTest(unittest.TestCase):
    """Validate local VCSum data helpers used by M7 service."""

    def test_load_vcsum_data_reads_jsonl_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_file = Path(temp_dir) / "sample.jsonl"
            rows = [
                {"id": "meeting_1", "summary": "one"},
                {"id": "meeting_2", "summary": "two"},
            ]
            data_file.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows),
                encoding="utf-8",
            )

            loaded = load_vcsum_data(str(data_file))

            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[0]["id"], "meeting_1")
            self.assertEqual(loaded[1]["summary"], "two")

    def test_format_transcript_supports_utterances_schema(self) -> None:
        meeting = {
            "utterances": [
                {"speaker": "Speaker 1", "text": {"zh": "你好"}},
                {"speaker": "Speaker 2", "text": {"zh": "收到"}},
            ]
        }

        formatted = format_transcript(meeting)

        self.assertIn("[Speaker 1]: 你好", formatted)
        self.assertIn("[Speaker 2]: 收到", formatted)

    def test_get_participants_returns_unique_sorted_speakers(self) -> None:
        meeting = {"speaker": [3, 1, 3, 2, 1]}

        participants = get_participants(meeting)

        self.assertEqual(participants, ["Speaker 1", "Speaker 2", "Speaker 3"])


if __name__ == "__main__":
    unittest.main()
