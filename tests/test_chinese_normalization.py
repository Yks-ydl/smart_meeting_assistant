from __future__ import annotations

import unittest

from core.chinese_utils import (
    normalize_simplified_chinese_payload,
    normalize_simplified_chinese_text,
)
from core.text_utils import clean_meeting_text
from gateway.main_server import (
    append_sentiment_turn,
    build_subtitle_from_audio_segment,
    normalize_gateway_payload,
)


class ChineseNormalizationTest(unittest.TestCase):
    def test_normalize_simplified_chinese_text_converts_traditional_characters(self) -> None:
        source = "這裡可以聽得見與會者的靜態錄音。"
        self.assertEqual(
            normalize_simplified_chinese_text(source),
            "这里可以听得见与会者的静态录音。",
        )

    def test_normalize_simplified_chinese_payload_preserves_structure(self) -> None:
        payload = {
            "summary": "這是一段總結",
            "items": ["與會者", {"snippet": "可以聽得見"}],
            "count": 2,
        }

        self.assertEqual(
            normalize_simplified_chinese_payload(payload),
            {
                "summary": "这是一段总结",
                "items": ["与会者", {"snippet": "可以听得见"}],
                "count": 2,
            },
        )

    def test_clean_meeting_text_also_normalizes_to_simplified(self) -> None:
        raw_text = "[00:01:23] 這裡\n\n可以聽得見\n"
        self.assertEqual(clean_meeting_text(raw_text), "这里\n\n可以听得见")

    def test_build_subtitle_from_audio_segment_normalizes_realtime_text(self) -> None:
        subtitle = build_subtitle_from_audio_segment(
            session_id="meeting-demo",
            index=0,
            segment={
                "speaker_label": "張三",
                "corrected_text": "可以聽得見這個靜態錄音。",
                "start_time": 1.2,
                "language": "zh",
            },
        )

        self.assertEqual(subtitle["speaker"], "张三")
        self.assertEqual(subtitle["text"], "可以听得见这个静态录音。")

    def test_append_sentiment_turn_normalizes_significant_moment_source_text(self) -> None:
        turns_ref = {"items": []}

        append_sentiment_turn(
            turns_ref,
            {
                "text": "這裡可以聽得見",
                "corrected_text": "這裡可以聽得見",
                "speaker_label": "李四",
                "start_time": 3.0,
                "end_time": 4.5,
                "language": "zh",
            },
        )

        self.assertEqual(
            turns_ref["items"],
            [
                {
                    "text": "这里可以听得见",
                    "corrected_text": "这里可以听得见",
                    "start_time": 3.0,
                    "end_time": 4.5,
                    "speaker_label": "李四",
                    "language": "zh",
                }
            ],
        )

    def test_normalize_gateway_payload_converts_nested_summary_action_and_sentiment_text(self) -> None:
        payload = {
            "summary": {"summary": "這是一個會議總結"},
            "actions": {
                "parsed_actions": [
                    {"task": "與家國同學對接", "assignee": "王五"},
                ]
            },
            "sentiment": {
                "significant_moments": [
                    {"snippet": "那就先做成靜態的吧", "speaker": "張三"},
                ]
            },
        }

        self.assertEqual(
            normalize_gateway_payload(payload),
            {
                "summary": {"summary": "这是一个会议总结"},
                "actions": {
                    "parsed_actions": [
                        {"task": "与家国同学对接", "assignee": "王五"},
                    ]
                },
                "sentiment": {
                    "significant_moments": [
                        {"snippet": "那就先做成静态的吧", "speaker": "张三"},
                    ]
                },
            },
        )


if __name__ == "__main__":
    unittest.main()