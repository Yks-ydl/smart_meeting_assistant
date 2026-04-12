from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from scripts.colab.colab_summary_service import ColabServiceSettings, create_app


class _FakeRuntime:
    # Keep runtime fake small so tests verify API contract only.
    model_name = "fake-model"

    def is_ready(self) -> bool:
        return True

    def summarize(self, text: str) -> str:
        return f"summary::{text}"


class ColabSummaryServiceContractTest(unittest.TestCase):
    def test_generate_endpoint_contract_without_auth(self) -> None:
        app = create_app(
            runtime=_FakeRuntime(),
            settings=ColabServiceSettings(auth_enabled=False),
        )
        client = TestClient(app)

        resp = client.post(
            "/api/v1/summary/generate",
            json={"session_id": "meeting-1", "text": "hello world"},
        )

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload.get("status"), "success")
        self.assertEqual(payload.get("session_id"), "meeting-1")
        self.assertIn("summary", payload)
        self.assertEqual(payload.get("mode"), "colab_remote")

    def test_generate_endpoint_requires_auth_when_enabled(self) -> None:
        app = create_app(
            runtime=_FakeRuntime(),
            settings=ColabServiceSettings(
                auth_enabled=True,
                auth_header="Authorization",
                auth_scheme="Bearer",
                auth_token="secret-token",
            ),
        )
        client = TestClient(app)

        resp = client.post(
            "/api/v1/summary/generate",
            json={"session_id": "meeting-2", "text": "hello"},
        )
        self.assertEqual(resp.status_code, 401)

        ok = client.post(
            "/api/v1/summary/generate",
            headers={"Authorization": "Bearer secret-token"},
            json={"session_id": "meeting-2", "text": "hello"},
        )
        self.assertEqual(ok.status_code, 200)

    def test_health_endpoint_reports_model_state(self) -> None:
        app = create_app(
            runtime=_FakeRuntime(),
            settings=ColabServiceSettings(auth_enabled=False),
        )
        client = TestClient(app)

        resp = client.get("/health")
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload.get("status"), "ok")
        self.assertTrue(payload.get("model_loaded"))
        self.assertEqual(payload.get("model_name"), "fake-model")


if __name__ == "__main__":
    unittest.main()
