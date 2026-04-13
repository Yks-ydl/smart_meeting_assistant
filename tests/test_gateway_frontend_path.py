from __future__ import annotations

import unittest
from pathlib import Path

from gateway.main_server import app, frontend_dir, resolve_frontend_dist_dir, resolve_project_root


class GatewayFrontendPathTest(unittest.TestCase):
    """Ensure gateway serves frontend bundle from assistant-local path."""

    def test_resolve_frontend_dist_dir_points_to_local_frontend(self) -> None:
        dist_dir = resolve_frontend_dist_dir()
        expected = resolve_project_root() / "frontend" / "dist"

        self.assertEqual(dist_dir, expected)
        self.assertEqual(dist_dir.name, "dist")

    def test_gateway_mounts_static_route_only_when_frontend_is_built(self) -> None:
        mounted_paths = {
            getattr(route, "path", None)
            for route in app.routes
            if getattr(route, "path", None)
        }

        if frontend_dir.is_dir():
            self.assertIn("/static", mounted_paths)
        else:
            self.assertNotIn("/static", mounted_paths)


if __name__ == "__main__":
    unittest.main()
