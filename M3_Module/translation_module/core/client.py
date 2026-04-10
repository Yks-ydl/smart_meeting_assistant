from __future__ import annotations

from typing import AsyncIterator, Iterable, Optional

from .factory import TranslatorFactory
from .interface import TranslationResult
from .tuning import TranslationTuningChannel


class TranslationClient:
    """唯一外部调用入口。

    对骨架系统只暴露 `TranslationClient`。
    内部如何选择 translator、如何应用调优 hook，均由客户端自行编排。
    """

    def __init__(
        self,
        src_lang: str = "en",
        tgt_lang: str = "zh",
        config_path: str = "config/translation.yml",
        mode: Optional[str] = None,
        tuning: Optional[TranslationTuningChannel] = None,
    ):
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang
        self.config_path = config_path
        self.mode = mode
        self.tuning = tuning or TranslationTuningChannel()
        self._translator = self._build_translator()

    def _build_translator(self):
        return TranslatorFactory.get_instance().get_translator(
            config_path=self.config_path,
            mode=self.mode,
        )

    def reload(self) -> None:
        """重载 translator（用于配置变更后刷新）。"""
        self._translator = self._build_translator()

    def set_languages(self, src_lang: str, tgt_lang: str) -> None:
        """更新默认语言对。"""
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang

    def switch_mode(self, mode: Optional[str]) -> None:
        """切换翻译模式并重建 translator。"""
        self.mode = mode
        self.reload()

    def set_tuning(self, tuning: TranslationTuningChannel) -> None:
        """替换调优通道。"""
        self.tuning = tuning

    def translate_result(
        self,
        text: str,
        src_lang: Optional[str] = None,
        tgt_lang: Optional[str] = None,
    ) -> TranslationResult:
        """返回完整翻译结果。"""
        resolved_src = src_lang or self.src_lang
        resolved_tgt = tgt_lang or self.tgt_lang
        return self._translator.translate(
            text,
            resolved_src,
            resolved_tgt,
            pre_hook=self.tuning.apply_pre,
            post_hook=self.tuning.apply_post,
        )

    def translate_text(
        self,
        text: str,
        src_lang: Optional[str] = None,
        tgt_lang: Optional[str] = None,
    ) -> str:
        """只返回翻译文本。"""
        return self.translate_result(text, src_lang, tgt_lang).text

    def translate_many(
        self,
        texts: Iterable[str],
        src_lang: Optional[str] = None,
        tgt_lang: Optional[str] = None,
    ) -> list[TranslationResult]:
        """批量同步翻译。"""
        return [self.translate_result(text, src_lang, tgt_lang) for text in texts]

    async def translate_stream(
        self,
        source_chunks: AsyncIterator[str],
        src_lang: Optional[str] = None,
        tgt_lang: Optional[str] = None,
    ) -> AsyncIterator[TranslationResult]:
        """流式翻译。"""
        resolved_src = src_lang or self.src_lang
        resolved_tgt = tgt_lang or self.tgt_lang
        async for result in self._translator.translate_stream(
            source_chunks,
            resolved_src,
            resolved_tgt,
            pre_hook=self.tuning.apply_pre,
            post_hook=self.tuning.apply_post,
        ):
            yield result

    # 兼容骨架习惯命名
    def sync_translate(
        self,
        text: str,
        src_lang: Optional[str] = None,
        tgt_lang: Optional[str] = None,
    ) -> TranslationResult:
        return self.translate_result(text, src_lang, tgt_lang)

    async def process_stream(
        self,
        source_chunks: AsyncIterator[str],
        src_lang: Optional[str] = None,
        tgt_lang: Optional[str] = None,
    ) -> AsyncIterator[TranslationResult]:
        async for result in self.translate_stream(source_chunks, src_lang, tgt_lang):
            yield result
