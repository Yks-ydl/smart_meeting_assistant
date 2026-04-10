"""DeepL 服务封装。"""

from __future__ import annotations

from typing import Optional

from .base import GenericHTTPTranslateService


class DeepLService(GenericHTTPTranslateService):
    """DeepL API 适配。

    默认请求与响应格式：
    - 请求字段：text, source_lang, target_lang
    - 响应路径：translations.0.text
    """

    def __init__(
        self,
        api_key: str,
        api_url: Optional[str] = None,
        timeout: float = 5.0,
    ):
        super().__init__(
            api_key=api_key,
            api_url=api_url or "https://api-free.deepl.com/v2/translate",
            timeout=timeout,
            auth_header="Authorization",
            key_prefix="DeepL-Auth-Key",
            text_field="text",
            src_lang_field="source_lang",
            tgt_lang_field="target_lang",
            response_text_path="translations.0.text",
            response_confidence_path=None,
        )

    def _build_payload(self, text: str, src_lang: str, tgt_lang: str) -> dict[str, object]:
        # DeepL 需要 text 为数组
        return {
            "text": [text],
            "source_lang": src_lang.upper(),
            "target_lang": tgt_lang.upper(),
        }

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
