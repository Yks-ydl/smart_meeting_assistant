from __future__ import annotations

import time
from typing import AsyncIterator, Optional

from ...core.interface import TranslationResult, TranslatorInterface
from ...utils.errors import TranslationError
from .services.base import GenericHTTPTranslateService
from .services.deepl import DeepLService
from .services.google import GoogleTranslateService
from .services.siliconflow import SiliconFlowService


class APITranslator(TranslatorInterface):
    """API 翻译器实现。"""

    def __init__(
        self,
        api_key: str,
        service: str = "deepl",
        batch_size: int = 3,
        api_url: Optional[str] = None,
        timeout: float = 5.0,
        auth_header: str = "Authorization",
        key_prefix: str = "Bearer",
        text_field: str = "text",
        src_lang_field: str = "src_lang",
        tgt_lang_field: str = "tgt_lang",
        response_text_path: str = "text",
        response_confidence_path: Optional[str] = None,
        model: str = "Qwen/Qwen2.5-7B-Instruct",
        temperature: float = 0.1,
        max_tokens: int = 512,
    ):
        self.api_key = api_key
        self.service = service.lower().strip()
        self.batch_size = batch_size
        self.timeout = timeout
        self.api_url = api_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._service_client = self._build_service_client(
            auth_header=auth_header,
            key_prefix=key_prefix,
            text_field=text_field,
            src_lang_field=src_lang_field,
            tgt_lang_field=tgt_lang_field,
            response_text_path=response_text_path,
            response_confidence_path=response_confidence_path,
        )

    def _build_service_client(
        self,
        auth_header: str,
        key_prefix: str,
        text_field: str,
        src_lang_field: str,
        tgt_lang_field: str,
        response_text_path: str,
        response_confidence_path: Optional[str],
    ):
        if self.service == "deepl":
            return DeepLService(api_key=self.api_key, api_url=self.api_url, timeout=self.timeout)
        if self.service == "google":
            return GoogleTranslateService(api_key=self.api_key, api_url=self.api_url, timeout=self.timeout)
        if self.service == "siliconflow":
            return SiliconFlowService(
                api_key=self.api_key,
                api_url=self.api_url or "https://api.siliconflow.cn/v1/chat/completions",
                model=self.model,
                timeout=self.timeout,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        return GenericHTTPTranslateService(
            api_key=self.api_key,
            api_url=self.api_url,
            timeout=self.timeout,
            auth_header=auth_header,
            key_prefix=key_prefix,
            text_field=text_field,
            src_lang_field=src_lang_field,
            tgt_lang_field=tgt_lang_field,
            response_text_path=response_text_path,
            response_confidence_path=response_confidence_path,
        )

    def translate(
        self,
        source_text: str,
        src_lang: str,
        tgt_lang: str,
        **kwargs,
    ) -> TranslationResult:
        start = time.perf_counter()
        pre_hook = kwargs.get("pre_hook")
        post_hook = kwargs.get("post_hook")

        text = source_text
        if callable(pre_hook):
            text = pre_hook(text)

        try:
            translated, confidence = self._service_client.translate(text, src_lang, tgt_lang)
        except Exception as exc:  # noqa: BLE001
            raise TranslationError(f"API translation failed: {exc}") from exc

        if callable(post_hook):
            translated = post_hook(translated)

        latency_ms = int((time.perf_counter() - start) * 1000)
        return TranslationResult(text=translated, confidence=confidence, is_final=True, latency_ms=latency_ms)

    async def translate_stream(
        self,
        source_chunks: AsyncIterator[str],
        src_lang: str,
        tgt_lang: str,
        **kwargs,
    ) -> AsyncIterator[TranslationResult]:
        pre_hook = kwargs.get("pre_hook")
        post_hook = kwargs.get("post_hook")

        async for chunk in source_chunks:
            start = time.perf_counter()
            text = chunk
            if callable(pre_hook):
                text = pre_hook(text)

            try:
                translated, confidence = await self._service_client.translate_async(text, src_lang, tgt_lang)
            except Exception as exc:  # noqa: BLE001
                raise TranslationError(f"API streaming translation failed: {exc}") from exc

            if callable(post_hook):
                translated = post_hook(translated)

            latency_ms = int((time.perf_counter() - start) * 1000)
            yield TranslationResult(
                text=translated,
                confidence=confidence,
                is_final=True,
                latency_ms=latency_ms,
            )
