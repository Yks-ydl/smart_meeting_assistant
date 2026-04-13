from __future__ import annotations

import time
from typing import Any, Optional

import httpx

from ...core.interface import SummarizerInterface, SummaryResult


class APISummarizer(SummarizerInterface):
    """API 摘要器。"""

    def __init__(
        self,
        api_key: str,
        service: str = "siliconflow",
        api_url: Optional[str] = None,
        timeout: float = 20.0,
        model: str = "Qwen/Qwen2.5-7B-Instruct",
        temperature: float = 0.2,
        max_tokens: int = 512,
        auth_header: str = "Authorization",
        key_prefix: str = "Bearer",
        text_field: str = "text",
        response_text_path: str = "text",
    ):
        self.api_key = api_key
        self.service = service.lower().strip()
        self.api_url = api_url or ""
        self.timeout = timeout
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.auth_header = auth_header
        self.key_prefix = key_prefix
        self.text_field = text_field
        self.response_text_path = response_text_path

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            token = f"{self.key_prefix} {self.api_key}".strip() if self.key_prefix else self.api_key
            headers[self.auth_header] = token
        return headers

    @staticmethod
    def _extract_by_path(data: dict[str, Any], path: str) -> Any:
        current: Any = data
        for part in path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def _siliconflow_payload(self, message: str) -> dict[str, object]:
        system_prompt = (
            "You are a professional meeting assistant. "
            "Summarize short multi-person dialogue in Chinese. "
            "Cover: who proposed what, each viewpoint, conflict/consensus, and action items/goals. "
            "Only output final summary text."
        )
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Dialogue:\n{message}"},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }

    def _parse_siliconflow(self, data: dict[str, Any]) -> str:
        choices = data.get("choices") or []
        if not choices:
            return ""
        return str(choices[0].get("message", {}).get("content", "")).strip()

    def summarize(self, message: str, **kwargs) -> SummaryResult:
        start = time.perf_counter()

        pre_hook = kwargs.get("pre_hook")
        post_hook = kwargs.get("post_hook")
        text = pre_hook(message) if callable(pre_hook) else message

        if self.api_url.startswith("mock://"):
            preview = text.replace("\n", " ")[:80]
            summary = f"[summary-mock] {preview}"
            latency_ms = int((time.perf_counter() - start) * 1000)
            return SummaryResult(text=summary, confidence=0.99, latency_ms=latency_ms)

        if self.service == "siliconflow":
            payload = self._siliconflow_payload(text)
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self.api_url, headers=self._headers(), json=payload)
                response.raise_for_status()
                data = response.json()
            summary = self._parse_siliconflow(data)
        else:
            payload = {self.text_field: text}
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self.api_url, headers=self._headers(), json=payload)
                response.raise_for_status()
                data = response.json()
            parsed = self._extract_by_path(data, self.response_text_path)
            summary = str(parsed if parsed is not None else data.get("summary") or data.get("text") or "")

        if callable(post_hook):
            summary = post_hook(summary)

        latency_ms = int((time.perf_counter() - start) * 1000)
        return SummaryResult(text=summary, confidence=0.9, latency_ms=latency_ms)
