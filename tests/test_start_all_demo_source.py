from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from start_all import build_service_catalog


class StartAllDemoSourceTest(unittest.TestCase):
    @staticmethod
    def _scripts(services: list[dict]) -> list[str]:
        return [service["script"] for service in services]

    def test_default_mode_skips_vcsum_data_service(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MEETING_DEMO_SOURCE", None)
            scripts = self._scripts(build_service_catalog())

        self.assertIn("services/audio_input_server.py", scripts)
        self.assertNotIn("services/data_server.py", scripts)

    def test_audio_mode_skips_vcsum_data_service(self) -> None:
        with patch.dict(os.environ, {"MEETING_DEMO_SOURCE": "audio"}, clear=False):
            scripts = self._scripts(build_service_catalog())

        self.assertIn("services/audio_input_server.py", scripts)
        self.assertNotIn("services/data_server.py", scripts)

    def test_vcsum_mode_keeps_data_service(self) -> None:
        with patch.dict(os.environ, {"MEETING_DEMO_SOURCE": "vcsum"}, clear=False):
            scripts = self._scripts(build_service_catalog())

        self.assertIn("services/audio_input_server.py", scripts)
        self.assertIn("services/data_server.py", scripts)