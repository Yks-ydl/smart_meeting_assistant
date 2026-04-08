"""NLLB 多语言翻译模型封装。"""

from __future__ import annotations

import importlib
from typing import Optional

from ....utils.errors import TranslationError, UnsupportedLanguageError


class NLLBModel:
    """基于 NLLB-200 的多语言翻译模型。

    默认模型：facebook/nllb-200-distilled-600M（适合本地部署与后续微调）。
    """

    _LANG_MAP = {
        "en": "eng_Latn",
        "en-us": "eng_Latn",
        "en-gb": "eng_Latn",
        "english": "eng_Latn",
        "zh": "zho_Hans",
        "zh-cn": "zho_Hans",
        "zh-hans": "zho_Hans",
        "chinese": "zho_Hans",
        "zh-tw": "zho_Hant",
        "zh-hant": "zho_Hant",
        "ja": "jpn_Jpan",
        "ko": "kor_Hang",
        "fr": "fra_Latn",
        "de": "deu_Latn",
        "es": "spa_Latn",
        "pt": "por_Latn",
        "ru": "rus_Cyrl",
        "it": "ita_Latn",
        "nl": "nld_Latn",
        "ar": "arb_Arab",
        "hi": "hin_Deva",
    }

    def __init__(
        self,
        model_id: str = "facebook/nllb-200-distilled-600M",
        device: str = "auto",
        max_new_tokens: int = 256,
    ):
        self.model_id = model_id
        self.device = device
        self.max_new_tokens = max_new_tokens

        self._tokenizer = None
        self._model = None
        self._torch = None

    def _lazy_load(self) -> None:
        if self._model is not None and self._tokenizer is not None:
            return
        try:
            transformers = importlib.import_module("transformers")
            self._torch = importlib.import_module("torch")
            AutoTokenizer = getattr(transformers, "AutoTokenizer")
            AutoModelForSeq2SeqLM = getattr(transformers, "AutoModelForSeq2SeqLM")

            self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            self._model = AutoModelForSeq2SeqLM.from_pretrained(self.model_id)

            resolved_device = self._resolve_device()
            if resolved_device != "cpu":
                self._model.to(resolved_device)
            self.device = resolved_device
        except ModuleNotFoundError as e:
            raise TranslationError(
                "NLLB backend requires transformers/torch. Install dependencies first."
            ) from e
        except Exception as e:
            raise TranslationError(f"Failed to load NLLB model '{self.model_id}': {e}") from e

    def _resolve_device(self) -> str:
        if self.device != "auto":
            return self.device
        torch = self._torch
        if torch is not None and torch.cuda.is_available():
            return "cuda"
        if torch is not None and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _to_nllb_lang(self, code: str, role: str) -> str:
        normalized = code.lower().strip()

        # 兼容误传的语言对格式（如 "zh-en" / "en-zh"）
        # 正确用法仍然是：src_lang="zh", tgt_lang="en"
        if "-" in normalized and normalized.count("-") == 1:
            left, right = normalized.split("-", 1)
            if len(left) in {2, 3} and len(right) in {2, 3}:
                normalized = left if role == "src" else right

        mapped = self._LANG_MAP.get(normalized)
        if mapped:
            return mapped
        # 用户可直接传 NLLB 格式语言码
        if "_" in code and len(code) >= 8:
            return code
        raise UnsupportedLanguageError(f"Unsupported NLLB language code: {code}")

    def translate(self, text: str, src_lang: str, tgt_lang: str, **kwargs) -> str:
        self._lazy_load()

        tokenizer = self._tokenizer
        model = self._model
        torch = self._torch
        if tokenizer is None or model is None or torch is None:
            raise TranslationError("NLLB model is not initialized")

        src = self._to_nllb_lang(src_lang, role="src")
        tgt = self._to_nllb_lang(tgt_lang, role="tgt")

        tokenizer.src_lang = src
        encoded = tokenizer(text, return_tensors="pt")
        if self.device != "cpu":
            encoded = {k: v.to(self.device) for k, v in encoded.items()}

        forced_bos_token_id = tokenizer.convert_tokens_to_ids(tgt)
        generated = model.generate(
            **encoded,
            forced_bos_token_id=forced_bos_token_id,
            max_new_tokens=kwargs.get("max_new_tokens", self.max_new_tokens),
            num_beams=kwargs.get("num_beams", 4),
        )
        return tokenizer.batch_decode(generated, skip_special_tokens=True)[0]
