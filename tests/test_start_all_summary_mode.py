from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from start_all import build_service_catalog


class StartAllSummaryModeTest(unittest.TestCase):
    def test_remote_mode_skips_local_summary_service(self) -> None:
        with patch.dict(os.environ, {"SUMMARY_EXECUTION_MODE": "remote"}, clear=False):
            services = build_service_catalog()

        scripts = [svc["script"] for svc in services]
        self.assertNotIn("services/summary_server.py", scripts)

    def test_local_mode_keeps_local_summary_service(self) -> None:
        with patch.dict(os.environ, {"SUMMARY_EXECUTION_MODE": "local"}, clear=False):
            services = build_service_catalog()

        scripts = [svc["script"] for svc in services]
        self.assertIn("services/summary_server.py", scripts)


if __name__ == "__main__":
    unittest.main()
