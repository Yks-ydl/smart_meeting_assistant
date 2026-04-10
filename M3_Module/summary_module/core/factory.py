from __future__ import annotations

from typing import Optional

from ..config.loader import ConfigLoader
from ..impl.api.api_summarizer import APISummarizer
from ..impl.local.local_summarizer import LocalSummarizer
from .interface import SummarizerInterface


class SummarizerFactory:
    _instance: Optional["SummarizerFactory"] = None
    _cache: dict[str, SummarizerInterface] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "SummarizerFactory":
        return cls()

    def get_summarizer(self, config_path: str = "config/summary.yml", mode: Optional[str] = None) -> SummarizerInterface:
        config = ConfigLoader.load(config_path)
        resolved_mode = mode or config.get("mode", "local")
        if resolved_mode not in {"api", "local"}:
            raise ValueError(f"Unsupported mode: {resolved_mode}. Expected 'api' or 'local'.")

        if resolved_mode in self._cache:
            return self._cache[resolved_mode]

        if resolved_mode == "api":
            api_cfg = config.get("api", {})
            summarizer = APISummarizer(
                api_key=api_cfg.get("api_key", ""),
                service=api_cfg.get("service", "siliconflow"),
                api_url=api_cfg.get("api_url"),
                timeout=api_cfg.get("timeout", 20.0),
                model=api_cfg.get("model", "Qwen/Qwen2.5-7B-Instruct"),
                temperature=api_cfg.get("temperature", 0.2),
                max_tokens=api_cfg.get("max_tokens", 512),
                auth_header=api_cfg.get("auth_header", "Authorization"),
                key_prefix=api_cfg.get("key_prefix", "Bearer"),
                text_field=api_cfg.get("text_field", "text"),
                response_text_path=api_cfg.get("response_text_path", "text"),
            )
        else:
            local_cfg = config.get("local", {})
            summarizer = LocalSummarizer(
                backend=local_cfg.get("backend", "mock"),
                model_name_or_path=local_cfg.get("model_name_or_path", ""),
                max_new_tokens=local_cfg.get("max_new_tokens", 256),
                temperature=local_cfg.get("temperature", 0.2),
                device=local_cfg.get("device", "auto"),
            )

        self._cache[resolved_mode] = summarizer
        return summarizer
