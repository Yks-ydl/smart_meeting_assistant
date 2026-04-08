from __future__ import annotations

from typing import Optional

from .interface import TranslatorInterface
from ..config.loader import ConfigLoader
from ..impl.api.api_translator import APITranslator
from ..impl.local.local_translator import LocalInferenceTranslator
from ..impl.local.llm_translator import LLMTranslator
from ..impl.local.models.llm import LLMModel


class TranslatorFactory:
    """翻译器工厂（单例）。"""

    _instance: Optional["TranslatorFactory"] = None
    _cache: dict[str, TranslatorInterface] = {}
    _model_cache: dict[str, "LLMModel"] = {}  # LLM 模型缓存，避免重复加载

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "TranslatorFactory":
        """获取单例实例。"""
        return cls()

    def get_translator(
        self,
        config_path: str = "config/translation.yml",
        mode: Optional[str] = None,
    ) -> TranslatorInterface:
        """根据配置获取翻译器实例。

        当前支持模式：
        - api: 调用远程 API 服务
        - local: 本地推理（可选择不同本地后端）
        """
        config = ConfigLoader.load(config_path)
        resolved_mode = mode or config.get("mode", "local")
        if resolved_mode not in {"api", "local"}:
            raise ValueError(f"Unsupported mode: {resolved_mode}. Expected 'api' or 'local'.")

        if resolved_mode == "api" and resolved_mode in self._cache:
            return self._cache[resolved_mode]

        if resolved_mode == "api":
            api_cfg = config.get("api", {})
            translator = APITranslator(
                api_key=api_cfg.get("api_key", ""),
                service=api_cfg.get("service", "deepl"),
                batch_size=api_cfg.get("batch_size", 3),
                api_url=api_cfg.get("api_url"),
                timeout=api_cfg.get("timeout", 5.0),
                auth_header=api_cfg.get("auth_header", "Authorization"),
                key_prefix=api_cfg.get("key_prefix", "Bearer"),
                text_field=api_cfg.get("text_field", "text"),
                src_lang_field=api_cfg.get("src_lang_field", "src_lang"),
                tgt_lang_field=api_cfg.get("tgt_lang_field", "tgt_lang"),
                response_text_path=api_cfg.get("response_text_path", "text"),
                response_confidence_path=api_cfg.get("response_confidence_path"),
                model=api_cfg.get("model", "Qwen/Qwen2.5-7B-Instruct"),
                temperature=api_cfg.get("temperature", 0.1),
                max_tokens=api_cfg.get("max_tokens", 512),
            )
            self._cache[resolved_mode] = translator
            return translator

        else:
            local_cfg = config.get("local", {})
            backend = (local_cfg.get("backend") or "stub").lower()
            cache_key = f"local:{backend}"
            if cache_key in self._cache:
                return self._cache[cache_key]

            if backend == "llm":
                llm_cfg = local_cfg.get("llm", config.get("llm", {}))

                model_id = llm_cfg.get("model_id", "Qwen/Qwen2.5-3B-Instruct")
                model_cache_key = f"{model_id}_{llm_cfg.get('quantization', 'none')}"

                if model_cache_key not in self._model_cache:
                    model = LLMModel(
                        model_id=model_id,
                        device=llm_cfg.get("device", "auto"),
                        quantization=llm_cfg.get("quantization"),
                        load_in_8bit=llm_cfg.get("load_in_8bit", False),
                        load_in_4bit=llm_cfg.get("load_in_4bit", False),
                        bnb_4bit_compute_dtype=llm_cfg.get("bnb_4bit_compute_dtype", "float16"),
                        bnb_4bit_quant_type=llm_cfg.get("bnb_4bit_quant_type", "nf4"),
                        bnb_4bit_use_double_quant=llm_cfg.get("bnb_4bit_use_double_quant", True),
                    )
                    self._model_cache[model_cache_key] = model

                translator = LLMTranslator(
                    model=self._model_cache[model_cache_key],
                    prompt_template=llm_cfg.get("prompt_template"),
                    lora_adapter_path=llm_cfg.get("lora_adapter_path"),
                    max_tokens=llm_cfg.get("max_tokens", 512),
                    temperature=llm_cfg.get("temperature", 0.3),
                    dev_channel=llm_cfg.get("dev_channel", {}),
                )
            else:
                translator = LocalInferenceTranslator(
                    model_path=local_cfg.get("model_path", ""),
                    quantized=local_cfg.get("quantized", True),
                    dev_channel=local_cfg.get("dev_channel", {}),
                    backend=backend,
                    multilingual_cfg=local_cfg.get("multilingual", {}),
                )

            self._cache[cache_key] = translator
            return translator
