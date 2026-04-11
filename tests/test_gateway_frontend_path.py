from __future__ import annotations

import unittest
from pathlib import Path

from gateway.main_server import resolve_frontend_dist_dir


class GatewayFrontendPathTest(unittest.TestCase):
    """Ensure gateway serves frontend bundle from assistant-local path."""

    def test_resolve_frontend_dist_dir_points_to_local_frontend(self) -> None:
        dist_dir = resolve_frontend_dist_dir()
        normalized = dist_dir.as_posix()

        self.assertTrue(normalized.endswith("smart_meeting_assistant/frontend/dist"))
        self.assertNotIn("/Code/", normalized)


if __name__ == "__main__":
    unittest.main()
