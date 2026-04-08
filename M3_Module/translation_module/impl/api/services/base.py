"""API 服务基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

import httpx


class BaseTranslateService(ABC):
    """第三方翻译服务基类。"""

    def __init__(
        self,
        api_key: str,
        api_url: Optional[str],
        timeout: float = 5.0,
        auth_header: str = "Authorization",
        key_prefix: str = "Bearer",
        text_field: str = "text",
        src_lang_field: str = "src_lang",
        tgt_lang_field: str = "tgt_lang",
        response_text_path: str = "text",
        response_confidence_path: Optional[str] = None,
    ):
        self.api_key = api_key
        self.api_url = api_url
        self.timeout = timeout
        self.auth_header = auth_header
        self.key_prefix = key_prefix
        self.text_field = text_field
        self.src_lang_field = src_lang_field
        self.tgt_lang_field = tgt_lang_field
        self.response_text_path = response_text_path
        self.response_confidence_path = response_confidence_path

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            value = f"{self.key_prefix} {self.api_key}".strip() if self.key_prefix else self.api_key
            headers[self.auth_header] = value
        return headers

    def _build_payload(self, text: str, src_lang: str, tgt_lang: str) -> dict[str, Any]:
        return {
            self.text_field: text,
            self.src_lang_field: src_lang,
            self.tgt_lang_field: tgt_lang,
        }

    def _extract_by_path(self, data: dict[str, Any], path: str) -> Any:
        current: Any = data
        for part in path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def _parse_response(self, payload: dict[str, Any]) -> tuple[str, float]:
        text = self._extract_by_path(payload, self.response_text_path)
        if text is None:
            text = payload.get("text") or payload.get("translation") or ""

        confidence = 1.0
        if self.response_confidence_path:
            conf_value = self._extract_by_path(payload, self.response_confidence_path)
            if conf_value is not None:
                try:
                    confidence = float(conf_value)
                except (TypeError, ValueError):
                    confidence = 1.0

        return str(text), confidence

    @abstractmethod
    def translate(self, text: str, src_lang: str, tgt_lang: str) -> tuple[str, float]:
        raise NotImplementedError

    @abstractmethod
    async def translate_async(self, text: str, src_lang: str, tgt_lang: str) -> tuple[str, float]:
        raise NotImplementedError


class GenericHTTPTranslateService(BaseTranslateService):
    """通用 HTTP 翻译服务。"""

    def translate(self, text: str, src_lang: str, tgt_lang: str) -> tuple[str, float]:
        if not self.api_url:
            return text, 0.0

        if self.api_url.startswith("mock://"):
            return f"[mock:{src_lang}->{tgt_lang}] {text}", 0.99

        payload = self._build_payload(text, src_lang, tgt_lang)
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(self.api_url, headers=self._build_headers(), json=payload)
            response.raise_for_status()
            data = response.json()
        return self._parse_response(data)

    async def translate_async(self, text: str, src_lang: str, tgt_lang: str) -> tuple[str, float]:
        if not self.api_url:
            return text, 0.0

        if self.api_url.startswith("mock://"):
            return f"[mock:{src_lang}->{tgt_lang}] {text}", 0.99

        payload = self._build_payload(text, src_lang, tgt_lang)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.api_url, headers=self._build_headers(), json=payload)
            response.raise_for_status()
            data = response.json()
        return self._parse_response(data)
