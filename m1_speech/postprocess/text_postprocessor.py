from __future__ import annotations

import re

from m1_speech.utils.config import PostProcessConfig
from m1_speech.utils.schemas import TranscriptSegment


class TextPostProcessor:
    """BTS 风格后处理占位模块。"""

    _EN_FILLERS = {
        "um",
        "uh",
        "erm",
        "ah",
        "you know",
        "i mean",
        "like",
    }

    def __init__(self, config: PostProcessConfig) -> None:
        self.config = config

    def process_segments(self, segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
        """对所有片段执行统一文本清洗。"""

        if not self.config.enabled:
            return segments

        for index, segment in enumerate(segments):
            previous_text = segments[index - 1].corrected_text if index > 0 else None
            segment.corrected_text = self.process_text(
                text=segment.text,
                language=segment.language,
                previous_text=previous_text,
            )

        return segments

    def process_text(self, text: str, language: str | None, previous_text: str | None = None) -> str:
        """对单条文本执行规则式 BTS 后处理。"""

        cleaned = text.strip()
        cleaned = self._collapse_spaces(cleaned)

        if self.config.remove_fillers and self._looks_like_english(language):
            cleaned = self._remove_fillers(cleaned)

        if self.config.capitalize and self._looks_like_english(language):
            cleaned = self._capitalize_sentence(cleaned)

        if self.config.restore_punctuation and self._looks_like_english(language):
            cleaned = self._restore_terminal_punctuation(cleaned)

        cleaned = self._contextual_rewrite(cleaned, previous_text=previous_text)
        return cleaned

    @staticmethod
    def _collapse_spaces(text: str) -> str:
        """压缩多余空白，保持输出整洁。"""

        return re.sub(r"\s+", " ", text).strip()

    def _remove_fillers(self, text: str) -> str:
        """移除常见英文口语赘词。"""

        cleaned = text
        for filler in sorted(self._EN_FILLERS, key=len, reverse=True):
            pattern = rf"\b{re.escape(filler)}\b[,\s]*"
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        cleaned = self._collapse_spaces(cleaned)
        return cleaned

    @staticmethod
    def _capitalize_sentence(text: str) -> str:
        """对英文句首进行简单首字母大写。"""

        if not text:
            return text
        return text[0].upper() + text[1:]

    @staticmethod
    def _restore_terminal_punctuation(text: str) -> str:
        """若英文句尾无标点，则补上句号。"""

        if not text:
            return text
        if text[-1] in ".!?":
            return text
        return f"{text}."

    @staticmethod
    def _looks_like_english(language: str | None) -> bool:
        """仅在英文场景下启用部分规则，避免误处理多语言文本。"""

        if language is None:
            return True
        return language.lower().startswith("en")

    @staticmethod
    def _contextual_rewrite(text: str, previous_text: str | None = None) -> str:
        """为未来 BTS / LLM-based correction 预留上下文增强接口。"""

        # TODO: Replace this rule-based placeholder with a stronger BTS-style
        # correction model, contextual rewriting model, or LLM-based editor.
        if previous_text and previous_text.endswith("?") and text and text[0].islower():
            return text[0].upper() + text[1:]
        return text

