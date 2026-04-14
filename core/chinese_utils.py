"""Chinese text normalization utilities shared across gateway and services.

Centralizing conversion keeps Simplified-Chinese enforcement in one place instead of
duplicating ad hoc conversions at each websocket or service boundary.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from opencc import OpenCC


_SIMPLIFIED_CONVERTER = OpenCC("t2s")


def normalize_simplified_chinese_text(text: str) -> str:
    """Convert Traditional Chinese characters to Simplified Chinese in one pass."""
    if not text:
        return text
    return _SIMPLIFIED_CONVERTER.convert(text)


def normalize_simplified_chinese_payload(value: Any) -> Any:
    """Recursively normalize string values while preserving payload structure."""
    if isinstance(value, str):
        return normalize_simplified_chinese_text(value)

    if isinstance(value, Mapping):
        return {
            key: normalize_simplified_chinese_payload(item)
            for key, item in value.items()
        }

    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [normalize_simplified_chinese_payload(item) for item in value]

    return value