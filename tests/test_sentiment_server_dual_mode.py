from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from services.sentiment_server import app


class SentimentServerDualModeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_realtime_single_utterance_mode(self) -> None:
        response = self.client.post(
            "/api/v1/sentiment/analyze",
            json={
                "session_id": "session-1",
                "speaker": "Alice",
                "text": "我同意这个方案，我们尽快推进。",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["speaker"], "Alice")
        self.assertEqual(payload["status"], "success")
        self.assertIn(payload["label"], {"positive", "neutral", "negative"})
        self.assertTrue(payload["signal"])

    def test_aggregate_meeting_mode(self) -> None:
        response = self.client.post(
            "/api/v1/sentiment/analyze",
            json=[
                {
                    "text": "我同意这个方案。",
                    "corrected_text": "我同意这个方案。",
                    "start_time": 0.0,
                    "end_time": 5.0,
                    "speaker_label": "Alice",
                    "language": "zh",
                },
                {
                    "text": "这个 deadline 太紧了。",
                    "corrected_text": "这个 deadline 太紧了。",
                    "start_time": 5.0,
                    "end_time": 10.0,
                    "speaker_label": "Bob",
                    "language": "zh",
                },
            ],
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["overall_summary"]["total_turns"], 2)
        self.assertIn("speaker_profiles", payload)
        self.assertIn("Alice", payload["speaker_profiles"])


if __name__ == "__main__":
    unittest.main()