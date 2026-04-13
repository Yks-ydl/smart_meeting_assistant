from __future__ import annotations

"""Smart Meeting Assistant - Real-Time Translation Module."""

from .core.interface import TranslationResult
from .core.tuning import TranslationTuningChannel
from .core.client import TranslationClient

def create_translation_client(
    src_lang: str = "en",
    tgt_lang: str = "zh",
    config_path: str = "config/translation.yml",
    mode: str | None = None,
    tuning: TranslationTuningChannel | None = None,
) -> TranslationClient:
    """创建高层调用客户端。"""
    return TranslationClient(
        src_lang=src_lang,
        tgt_lang=tgt_lang,
        config_path=config_path,
        mode=mode,
        tuning=tuning,
    )


__all__ = [
    "TranslationResult",
    "TranslationTuningChannel",
    "TranslationClient",
    "create_translation_client",
]
