"""Google Translate 服务封装。"""

from __future__ import annotations

from typing import Optional

from .base import GenericHTTPTranslateService


class GoogleTranslateService(GenericHTTPTranslateService):
    """Google Translate API 适配。"""

    def __init__(
        self,
        api_key: str,
        api_url: Optional[str] = None,
        timeout: float = 5.0,
    ):
        super().__init__(
            api_key=api_key,
            api_url=api_url or "https://translation.googleapis.com/language/translate/v2",
            timeout=timeout,
            auth_header="X-Goog-Api-Key",
            key_prefix="",
            text_field="q",
            src_lang_field="source",
            tgt_lang_field="target",
            response_text_path="data.translations.0.translatedText",
            response_confidence_path=None,
        )

    def _extract_by_path(self, data: dict[str, object], path: str):
        current = data
        for part in path.split("."):
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                    continue
                return None
            if isinstance(current, list):
                try:
                    idx = int(part)
                except ValueError:
                    return None
                if idx < 0 or idx >= len(current):
                    return None
                current = current[idx]
                continue
            return None
        return current
