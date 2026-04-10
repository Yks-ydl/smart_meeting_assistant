from __future__ import annotations

import time

from ...core.interface import SummarizerInterface, SummaryResult
from .models import build_local_summary_model


class LocalSummarizer(SummarizerInterface):
    """本地摘要器（模型推理版）。"""

    def __init__(
        self,
        backend: str = "local",
        model_name_or_path: str = "",
        max_new_tokens: int = 256,
        temperature: float = 0.2,
        device: str = "auto",
    ):
        self.backend = backend
        self.model = build_local_summary_model(
            backend=backend,
            model_name_or_path=model_name_or_path,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            device=device,
        )

    @staticmethod
    def _build_prompt(message: str) -> str:
        return (
            "【会议对话】\n"
            f"{message}\n\n"
            "【会议纪要】\n"
        )

    def summarize(self, message: str, **kwargs) -> SummaryResult:
        start = time.perf_counter()
        text = message
        pre_hook = kwargs.get("pre_hook")
        post_hook = kwargs.get("post_hook")

        if callable(pre_hook):
            text = pre_hook(text)

        prompt = self._build_prompt(text)
        summary = self.model.generate(prompt)

        if callable(post_hook):
            summary = post_hook(summary)

        latency_ms = int((time.perf_counter() - start) * 1000)
        return SummaryResult(text=summary, confidence=0.8, latency_ms=latency_ms)
