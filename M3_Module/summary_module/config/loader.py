"""配置加载器。"""

import os
import re
from pathlib import Path
from typing import Any

import yaml


class ConfigLoader:
    _env_pattern = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

    @classmethod
    def _expand_env(cls, value: Any) -> Any:
        if isinstance(value, str):
            def replace(match: re.Match[str]) -> str:
                env_key = match.group(1)
                return os.getenv(env_key, "")

            return cls._env_pattern.sub(replace, value)
        if isinstance(value, dict):
            return {k: cls._expand_env(v) for k, v in value.items()}
        if isinstance(value, list):
            return [cls._expand_env(v) for v in value]
        return value

    @staticmethod
    def load(config_path: str) -> dict[str, Any]:
        path = Path(config_path)
        if not path.is_absolute() and not path.exists():
            package_root = Path(__file__).resolve().parents[1]
            path = package_root / config_path
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        return ConfigLoader._expand_env(raw)
