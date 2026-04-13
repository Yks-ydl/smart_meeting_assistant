from __future__ import annotations

from typing import Protocol


class LocalSummaryModel(Protocol):
    """本地摘要模型协议。"""

    def generate(self, prompt: str) -> str:
        ...
