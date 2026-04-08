from __future__ import annotations

from typing import Optional

from .factory import SummarizerFactory
from .interface import SummaryResult


class SummaryClient:
    """对外摘要入口。"""

    def __init__(
        self,
        config_path: str = "config/summary.yml",
        mode: Optional[str] = None,
    ):
        self.config_path = config_path
        self.mode = mode
        self._summarizer = self._build_summarizer()

    def _build_summarizer(self):
        return SummarizerFactory.get_instance().get_summarizer(
            config_path=self.config_path,
            mode=self.mode,
        )

    def reload(self) -> None:
        self._summarizer = self._build_summarizer()

    def switch_mode(self, mode: Optional[str]) -> None:
        self.mode = mode
        self.reload()

    def summarize_result(self, message: str) -> SummaryResult:
        return self._summarizer.summarize(message)

    def summarize_text(self, message: str) -> str:
        return self.summarize_result(message).text
