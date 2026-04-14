from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from gateway.demo_source import resolve_meeting_demo_source, use_vcsum_demo_source
from gateway.main_server import (
    build_directory_pipeline_request,
    build_demo_audio_request,
    resolve_demo_audio_input_dir,
    resolve_project_root,
)


class GatewayDemoSourceConfigTest(unittest.TestCase):
    def test_demo_source_defaults_to_audio(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MEETING_DEMO_SOURCE", None)

            self.assertEqual(resolve_meeting_demo_source(), "audio")
            self.assertFalse(use_vcsum_demo_source())

    def test_demo_source_requires_explicit_vcsum_opt_in(self) -> None:
        with patch.dict(os.environ, {"MEETING_DEMO_SOURCE": "vcsum"}, clear=False):
            self.assertEqual(resolve_meeting_demo_source(), "vcsum")
            self.assertTrue(use_vcsum_demo_source())

        with patch.dict(os.environ, {"MEETING_DEMO_SOURCE": "legacy"}, clear=False):
            self.assertEqual(resolve_meeting_demo_source(), "audio")
            self.assertFalse(use_vcsum_demo_source())

    def test_resolve_demo_audio_input_dir_prefers_request_path(self) -> None:
        with patch.dict(os.environ, {"MEETING_AUDIO_INPUT_DIR": "from-env"}, clear=False):
            resolved = resolve_demo_audio_input_dir("custom-audio")

        self.assertEqual(resolved, resolve_project_root() / "custom-audio")

    def test_build_demo_audio_request_uses_audio_defaults(self) -> None:
        with patch.dict(
            os.environ,
            {
                "MEETING_AUDIO_INPUT_DIR": "meeting-audio",
                "MEETING_AUDIO_GLOB_PATTERN": "*.wav",
                "MEETING_AUDIO_RECURSIVE": "yes",
            },
            clear=False,
        ):
            request = build_demo_audio_request("meeting-demo", None)

        self.assertEqual(request["session_id"], "meeting-demo")
        self.assertEqual(Path(request["input_dir"]), resolve_project_root() / "meeting-audio")
        self.assertEqual(request["glob_pattern"], "*.wav")
        self.assertTrue(request["recursive"])

    def test_directory_pipeline_request_defaults_to_supported_suffix_discovery(self) -> None:
        request = build_directory_pipeline_request({"session_id": "meeting-demo"})

        self.assertEqual(request.session_id, "meeting-demo")
        self.assertEqual(request.glob_pattern, "*")