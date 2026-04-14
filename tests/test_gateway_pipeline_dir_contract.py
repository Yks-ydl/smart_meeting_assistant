from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from gateway.main_server import app


def build_audio_result(segments: list[dict]) -> dict:
    return {
        "status": "success",
        "session_id": "session-test",
        "mode": "independent_tracks_from_directory",
        "input_dir": "audio",
        "merged_transcript": segments,
        "full_text": "\n".join(
            f"[{segment['speaker_label']}]: {segment['corrected_text']}" for segment in segments
        ),
        "errors": [],
    }


class GatewayDirectoryPipelineContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_pipeline_streams_expected_message_types(self) -> None:
        service_calls: list[tuple[str, object]] = []

        async def fake_call_service(client, url, payload=None, method="POST", timeout=30.0):
            service_calls.append((url, payload))
            if url.endswith("/audio/process_directory"):
                return build_audio_result(
                    [
                        {
                            "speaker_label": "Alice",
                            "corrected_text": "大家好，我们开始周会。",
                            "language": "zh",
                            "start_time": 0.0,
                            "end_time": 12.0,
                            "source_channel": "track-a",
                        },
                        {
                            "speaker_label": "Bob",
                            "corrected_text": "我会在周五前完成接口说明。",
                            "language": "zh",
                            "start_time": 12.0,
                            "end_time": 24.0,
                            "source_channel": "track-b",
                        },
                        {
                            "speaker_label": "Carol",
                            "corrected_text": "下周三安排联调。",
                            "language": "zh",
                            "start_time": 24.0,
                            "end_time": 36.0,
                            "source_channel": "track-c",
                        },
                    ]
                )
            if url.endswith("/translation/translate"):
                return {
                    "status": "success",
                    "translated_text": f"EN:{payload['text']}",
                }
            if url.endswith("/translation/extract_actions"):
                return {
                    "status": "success",
                    "parsed_actions": [
                        {
                            "task": "整理联调计划",
                            "assignee": "Carol",
                            "deadline": "下周三",
                        }
                    ],
                }
            if url.endswith("/sentiment/analyze"):
                return {
                    "overall_summary": {
                        "total_turns": len(payload or []),
                        "dominant_signals": ["agreement"],
                        "atmosphere": "Positive/Constructive",
                    },
                    "speaker_profiles": {},
                    "significant_moments": [],
                }
            raise AssertionError(f"Unexpected service URL: {url}")

        async def fake_call_summary_service(client, summary_url, payload, config):
            return {"summary": f"SUMMARY::{payload['text']}"}

        with patch("gateway.main_server.call_service", new=fake_call_service), patch(
            "gateway.main_server.call_summary_service", new=fake_call_summary_service
        ), patch.dict(os.environ, {"GATEWAY_REPLAY_DELAY_SEC": "0"}, clear=False):
            with self.client.websocket_connect("/ws/pipeline/dir") as websocket:
                websocket.send_json(
                    {
                        "session_id": "session-1",
                        "input_dir": "audio",
                        "glob_pattern": "*.wav",
                        "target_lang": "en",
                        "enable_translation": True,
                        "enable_actions": True,
                        "enable_sentiment": True,
                    }
                )

                received_types: list[str] = []
                meeting_end_report = None
                while True:
                    message = websocket.receive_json()
                    received_types.append(message["type"])
                    if message["type"] == "meeting_end_report":
                        meeting_end_report = message
                        break

        self.assertEqual(received_types[0], "info")
        self.assertIn("asr_result", received_types)
        self.assertIn("analysis_result", received_types)
        self.assertIn("action_result", received_types)
        self.assertEqual(received_types[-1], "meeting_end_report")
        self.assertIsNotNone(meeting_end_report)
        self.assertIn("SUMMARY::", meeting_end_report["data"]["summary"]["summary"])

        audio_request_payload = next(
            payload
            for url, payload in service_calls
            if url.endswith("/audio/process_directory")
        )
        self.assertEqual(audio_request_payload["glob_pattern"], "*.wav")

    def test_manual_end_uses_only_emitted_segments_for_final_summary(self) -> None:
        summary_payloads: list[str] = []

        async def fake_call_service(client, url, payload=None, method="POST", timeout=30.0):
            if url.endswith("/audio/process_directory"):
                return build_audio_result(
                    [
                        {
                            "speaker_label": "Alice",
                            "corrected_text": "第一段输出。",
                            "language": "zh",
                            "start_time": 0.0,
                            "end_time": 10.0,
                            "source_channel": "track-a",
                        },
                        {
                            "speaker_label": "Bob",
                            "corrected_text": "第二段不应进入最终总结。",
                            "language": "zh",
                            "start_time": 10.0,
                            "end_time": 20.0,
                            "source_channel": "track-b",
                        },
                        {
                            "speaker_label": "Carol",
                            "corrected_text": "第三段也不应进入最终总结。",
                            "language": "zh",
                            "start_time": 20.0,
                            "end_time": 30.0,
                            "source_channel": "track-c",
                        },
                    ]
                )
            if url.endswith("/translation/extract_actions"):
                return {"status": "success", "parsed_actions": []}
            if url.endswith("/sentiment/analyze"):
                return {
                    "overall_summary": {
                        "total_turns": len(payload or []),
                        "dominant_signals": [],
                        "atmosphere": "Positive/Constructive",
                    },
                    "speaker_profiles": {},
                    "significant_moments": [],
                }
            raise AssertionError(f"Unexpected service URL: {url}")

        async def fake_call_summary_service(client, summary_url, payload, config):
            summary_payloads.append(payload["text"])
            return {"summary": payload["text"]}

        with patch("gateway.main_server.call_service", new=fake_call_service), patch(
            "gateway.main_server.call_summary_service", new=fake_call_summary_service
        ), patch.dict(os.environ, {"GATEWAY_REPLAY_DELAY_SEC": "0.2"}, clear=False):
            with self.client.websocket_connect("/ws/pipeline/dir") as websocket:
                websocket.send_json(
                    {
                        "session_id": "session-2",
                        "input_dir": "audio",
                        "glob_pattern": "*.m4a",
                        "target_lang": "en",
                        "enable_translation": False,
                        "enable_actions": False,
                        "enable_sentiment": False,
                    }
                )

                self.assertEqual(websocket.receive_json()["type"], "info")
                self.assertEqual(websocket.receive_json()["type"], "info")
                first_segment = websocket.receive_json()
                self.assertEqual(first_segment["type"], "asr_result")

                websocket.send_json({"type": "end_meeting"})

                meeting_end_report = None
                while True:
                    message = websocket.receive_json()
                    if message["type"] == "meeting_end_report":
                        meeting_end_report = message
                        break

        self.assertEqual(summary_payloads, ["[Alice]: 第一段输出。"])
        self.assertIsNotNone(meeting_end_report)
        self.assertEqual(
            meeting_end_report["data"]["summary"]["summary"],
            "[Alice]: 第一段输出。",
        )


if __name__ == "__main__":
    unittest.main()