from __future__ import annotations

import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from gateway.main_server import (
    build_service_endpoints,
    build_summary_request_config,
    call_summary_service,
)


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def json(self) -> dict:
        return self._payload


class _FlakyClient:
    def __init__(self, fail_times: int):
        self.fail_times = fail_times
        self.calls = 0

    async def post(self, url: str, json: dict, timeout: float, headers: dict | None = None):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("temporary network error")
        return _FakeResponse({"status": "success", "summary": "ok", "url": url})


class GatewaySummaryRemoteConfigTest(unittest.TestCase):
    def test_summary_service_url_defaults_to_local(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SUMMARY_SERVICE_URL", None)
            endpoints = build_service_endpoints()

        self.assertEqual(
            endpoints["summary"],
            "http://127.0.0.1:8002/api/v1/summary/generate",
        )

    def test_summary_service_url_can_be_overridden(self) -> None:
        custom_url = "https://example-colab.ngrok-free.app/api/v1/summary/generate"
        with patch.dict(os.environ, {"SUMMARY_SERVICE_URL": custom_url}, clear=False):
            endpoints = build_service_endpoints()

        self.assertEqual(endpoints["summary"], custom_url)

    def test_summary_request_config_includes_auth_header(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SUMMARY_REMOTE_TIMEOUT_SEC": "95",
                "SUMMARY_REMOTE_RETRIES": "2",
                "SUMMARY_REMOTE_AUTH_HEADER": "Authorization",
                "SUMMARY_REMOTE_AUTH_SCHEME": "Bearer",
                "SUMMARY_REMOTE_AUTH_TOKEN": "abc-token",
            },
            clear=False,
        ):
            cfg = build_summary_request_config()

        self.assertEqual(cfg.timeout_sec, 95.0)
        self.assertEqual(cfg.retries, 2)
        self.assertEqual(cfg.headers.get("Authorization"), "Bearer abc-token")

    def test_call_summary_service_retries_and_succeeds(self) -> None:
        endpoints = {"summary": "https://example-colab.ngrok-free.app/api/v1/summary/generate"}
        cfg = SimpleNamespace(timeout_sec=20.0, retries=2, headers={})
        client = _FlakyClient(fail_times=1)

        result = asyncio.run(
            call_summary_service(
                client=client,
                summary_url=endpoints["summary"],
                payload={"session_id": "s1", "text": "hello"},
                config=cfg,
            )
        )

        self.assertEqual(result.get("status"), "success")
        self.assertEqual(client.calls, 2)

    def test_call_summary_service_returns_error_after_exhausted_retries(self) -> None:
        cfg = SimpleNamespace(timeout_sec=20.0, retries=1, headers={})
        client = _FlakyClient(fail_times=3)

        result = asyncio.run(
            call_summary_service(
                client=client,
                summary_url="https://example-colab.ngrok-free.app/api/v1/summary/generate",
                payload={"session_id": "s2", "text": "hello"},
                config=cfg,
            )
        )

        self.assertIn("error", result)
        self.assertEqual(client.calls, 2)


if __name__ == "__main__":
    unittest.main()
