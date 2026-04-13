"""Local summary model backends."""

from .base import LocalSummaryModel
from .factory import build_local_summary_model

__all__ = ["LocalSummaryModel", "build_local_summary_model"]
