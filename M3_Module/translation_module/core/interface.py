from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass
class TranslationResult:
    """翻译结果数据类。"""

    text: str
    confidence: float = 1.0
    is_final: bool = False
    src_offset: tuple[int, int] = (0, 0)
    latency_ms: int = 0


class TranslatorInterface(ABC):
    """翻译器抽象接口。"""

    @abstractmethod
    def translate(
        self,
        source_text: str,
        src_lang: str,
        tgt_lang: str,
        **kwargs,
    ) -> TranslationResult:
        """同步翻译接口。"""
        raise NotImplementedError

    @abstractmethod
    async def translate_stream(
        self,
        source_chunks: AsyncIterator[str],
        src_lang: str,
        tgt_lang: str,
        **kwargs,
    ) -> AsyncIterator[TranslationResult]:
        """异步流式翻译接口。"""
        raise NotImplementedError
