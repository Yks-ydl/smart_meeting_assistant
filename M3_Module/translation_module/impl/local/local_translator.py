from __future__ import annotations

import time
from typing import AsyncIterator, Callable, Optional

from ...core.interface import TranslationResult, TranslatorInterface
from ...utils.errors import TranslationError
from .models.nllb import NLLBModel


class LocalInferenceTranslator(TranslatorInterface):
    """本地推理翻译器实现（可调结构版）。"""

    def __init__(
        self,
        model_path: str,
        quantized: bool = True,
        dev_channel: Optional[dict] = None,
        backend: str = "stub",
        multilingual_cfg: Optional[dict] = None,
    ):
        self.model_path = model_path
        self.quantized = quantized
        self.dev_channel = dev_channel or {}
        self.backend = backend.lower().strip()
        self.multilingual_cfg = multilingual_cfg or {}
        self._model = self._build_backend_model()

    def _build_backend_model(self):
        if self.backend == "nllb":
            return NLLBModel(
                model_id=self.multilingual_cfg.get("model_id", "facebook/nllb-200-distilled-600M"),
                device=self.multilingual_cfg.get("device", "auto"),
                max_new_tokens=self.multilingual_cfg.get("max_new_tokens", 256),
            )
        if self.backend in {"stub", "dev"}:
            return None
        raise TranslationError(f"Unsupported local backend: {self.backend}")

    def _normalize_lang_pair(self, src_lang: str, tgt_lang: str) -> tuple[str, str]:
        return src_lang.lower().strip(), tgt_lang.lower().strip()

    def _apply_glossary(self, text: str, glossary: dict[str, str]) -> str:
        translated = text
        for src, tgt in glossary.items():
            translated = translated.replace(src, tgt)
        return translated

    def _dev_translate(self, text: str, src_lang: str, tgt_lang: str) -> str:
        """内部可调通道：便于你后续直接在此迭代效果。"""
        src, tgt = self._normalize_lang_pair(src_lang, tgt_lang)
        glossary = self.dev_channel.get("glossary", {})

        # 这里是故意留给你迭代效果的核心入口。
        # 当前实现：
        # 1) 若存在词汇表，先按词汇表替换
        # 2) 没命中时返回结构化占位文本，便于观察语言路由是否正确
        candidate = self._apply_glossary(text, glossary) if glossary else text
        if candidate != text:
            return candidate

        return f"[local:{src}->{tgt}] {text}"

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

        if self.backend == "nllb" and self._model is not None:
            translated = self._model.translate(
                text,
                src_lang,
                tgt_lang,
                max_new_tokens=kwargs.get("max_new_tokens", self.multilingual_cfg.get("max_new_tokens", 256)),
                num_beams=kwargs.get("num_beams", self.multilingual_cfg.get("num_beams", 4)),
            )
            confidence = 0.9
        else:
            translated = self._dev_translate(text, src_lang, tgt_lang)
            confidence = 0.5

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
        async for chunk in source_chunks:
            yield self.translate(chunk, src_lang, tgt_lang, **kwargs)
