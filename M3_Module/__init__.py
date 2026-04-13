from __future__ import annotations

"""M3_Module package root.

This package re-exports the public entry points from the translation and
summary modules so callers can import from the project root directly.
"""

from summary_module import SummaryClient, SummaryResult, create_summary_client
from translation_module import (
    TranslationClient,
    TranslationResult,
    TranslationTuningChannel,
    create_translation_client,
)

__all__ = [
    "SummaryClient",
    "SummaryResult",
    "TranslationClient",
    "TranslationResult",
    "TranslationTuningChannel",
    "create_summary_client",
    "create_translation_client",
]
