from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from services.data_server import DataServiceState


class DataServerStateConfigTest(unittest.TestCase):
    """Ensure M7 service resolves dataset paths from local config, not Code folder."""

    def test_data_paths_can_be_overridden_by_env(self) -> None:
        with patch.dict(
            os.environ,
            {
                "VCSUM_SHORT_DATA_PATH": "D:/tmp/custom_short.txt",
                "VCSUM_LONG_DATA_PATH": "D:/tmp/custom_long.txt",
            },
            clear=False,
        ):
            state = DataServiceState()

        self.assertEqual(state.short_data_path, Path("D:/tmp/custom_short.txt"))
        self.assertEqual(state.long_data_path, Path("D:/tmp/custom_long.txt"))

    def test_default_paths_point_to_project_vcsum_data(self) -> None:
        with patch.dict(
            os.environ,
            {
                "VCSUM_SHORT_DATA_PATH": "",
                "VCSUM_LONG_DATA_PATH": "",
            },
            clear=False,
        ):
            state = DataServiceState()

        short_norm = state.short_data_path.as_posix()
        long_norm = state.long_data_path.as_posix()
        self.assertTrue(short_norm.endswith("VCSum/vcsum_data/short_train.txt"))
        self.assertTrue(long_norm.endswith("VCSum/vcsum_data/long_train.txt"))


if __name__ == "__main__":
    unittest.main()
