from __future__ import annotations

"""可直接运行的本地翻译调用示例（非 pytest 单测）。

运行示例：
python translation_module/tests/demo_local_usage.py --backend stub
python translation_module/tests/demo_local_usage.py --backend nllb --src en --tgt zh
python translation_module/tests/demo_local_usage.py --backend llm --src zh --tgt en
"""

import argparse
import sys
import tempfile
from pathlib import Path

import yaml

if __package__ is None or __package__ == "":
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from translation_module import TranslationClient


def build_config_for_backend(base_config: Path, backend: str) -> str:
    with base_config.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    cfg["mode"] = "local"
    cfg.setdefault("local", {})
    cfg["local"]["backend"] = backend

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False, encoding="utf-8") as tf:
        yaml.safe_dump(cfg, tf, allow_unicode=True, sort_keys=False)
        return tf.name


def main() -> None:
    # 1) 输入变量声明
    parser = argparse.ArgumentParser(description="Local translation demo")
    parser.add_argument("--backend", choices=["stub", "nllb", "llm"], default="stub")
    parser.add_argument("--src", default="en")
    parser.add_argument("--tgt", default="zh")
    parser.add_argument("--text", default="Hello team, we reached consensus on the deadline.")
    args = parser.parse_args()

    source_text: str = args.text
    src_lang: str = args.src
    tgt_lang: str = args.tgt
    backend: str = args.backend

    # 2) 创建翻译模块实例
    base_cfg = Path("translation_module/config/translation.yml")
    temp_cfg_path = build_config_for_backend(base_cfg, backend)
    client = TranslationClient(
        src_lang=src_lang,
        tgt_lang=tgt_lang,
        config_path=temp_cfg_path,
        mode="local",
    )

    # 3) 传入变量并执行
    result = client.translate_result(
        text=source_text,
        src_lang=src_lang,
        tgt_lang=tgt_lang,
    )

    # 4) 打印输出
    print("=" * 60)
    print("Local Translation Demo")
    print("=" * 60)
    print(f"backend     : {backend}")
    print(f"source lang : {src_lang}")
    print(f"target lang : {tgt_lang}")
    print(f"input text  : {source_text}")
    print("-" * 60)
    print(f"output text : {result.text}")
    print(f"confidence  : {result.confidence:.2f}")
    print(f"latency(ms) : {result.latency_ms}")
    print("=" * 60)


if __name__ == "__main__":
    main()
