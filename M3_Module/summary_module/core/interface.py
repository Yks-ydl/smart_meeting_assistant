from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SummaryResult:
    """摘要结果。"""

    text: str
    confidence: float = 1.0
    latency_ms: int = 0


class SummarizerInterface(ABC):
    """摘要器抽象接口。"""

    @abstractmethod
    def summarize(self, message: str, **kwargs) -> SummaryResult:
        raise NotImplementedError
