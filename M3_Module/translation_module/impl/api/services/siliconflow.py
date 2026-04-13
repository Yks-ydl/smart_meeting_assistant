from __future__ import annotations

from typing import Optional

import httpx


class SiliconFlowService:
    """SiliconFlow Chat Completions 翻译服务。"""

    def __init__(
        self,
        api_key: str,
        api_url: str,
        model: str = "Qwen/Qwen2.5-7B-Instruct",
        timeout: float = 20.0,
        temperature: float = 0.1,
        max_tokens: int = 512,
    ):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _payload(self, text: str, src_lang: str, tgt_lang: str) -> dict[str, object]:
        system_prompt = (
            "You are a professional meeting translation engine. "
            "Translate user input accurately and naturally. "
            "Only output translated text, no explanations."
        )
        user_prompt = (
            f"Source language: {src_lang}\n"
            f"Target language: {tgt_lang}\n"
            f"Text: {text}"
        )
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }

    @staticmethod
    def _parse_result(data: dict) -> tuple[str, float]:
        choices = data.get("choices") or []
        if not choices:
            return "", 0.0

        content = (
            choices[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        return content, 0.95

    def translate(self, text: str, src_lang: str, tgt_lang: str) -> tuple[str, float]:
        if self.api_url.startswith("mock://"):
            return f"[siliconflow-mock:{src_lang}->{tgt_lang}] {text}", 0.99

        payload = self._payload(text, src_lang, tgt_lang)
        print(f"SiliconFlowService.translate payload: {payload}")  # Debug log
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(self.api_url, headers=self._headers(), json=payload)
            response.raise_for_status()
            data = response.json()
        return self._parse_result(data)

    async def translate_async(self, text: str, src_lang: str, tgt_lang: str) -> tuple[str, float]:
        if self.api_url.startswith("mock://"):
            return f"[siliconflow-mock:{src_lang}->{tgt_lang}] {text}", 0.99

        payload = self._payload(text, src_lang, tgt_lang)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.api_url, headers=self._headers(), json=payload)
            response.raise_for_status()
            data = response.json()
        return self._parse_result(data)
