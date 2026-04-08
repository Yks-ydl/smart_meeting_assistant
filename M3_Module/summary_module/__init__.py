from __future__ import annotations

"""Smart Meeting Assistant - Dialogue Summary Module."""

from .core.client import SummaryClient
from .core.interface import SummaryResult


def create_summary_client(
    config_path: str = "config/summary.yml",
    mode: str | None = None,
) -> SummaryClient:
    return SummaryClient(config_path=config_path, mode=mode)


__all__ = ["SummaryClient", "SummaryResult", "create_summary_client"]
