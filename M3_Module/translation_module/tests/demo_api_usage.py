from __future__ import annotations

"""可直接运行的 API 调用示例（非 pytest 单测）。

运行：
python translation_module/tests/demo_api_usage.py
"""

import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from translation_module import TranslationClient


def main() -> None:
    # 1) 输入变量声明
    config_path: str = "translation_module/config/translation.yml"
    mode: str = "api"
    src_lang: str = "en"
    tgt_lang: str = "zh"
    source_text: str = "Hello team, we reached consensus on the deadline."

    # 2) 创建翻译模块实例
    client = TranslationClient(
        src_lang=src_lang,
        tgt_lang=tgt_lang,
        config_path=config_path,
        mode=mode,
    )

    # 3) 传入变量并执行
    result = client.translate_result(
        text=source_text,
        src_lang=src_lang,
        tgt_lang=tgt_lang,
    )

    # 4) 打印输出
    print("=" * 60)
    print("API Translation Demo")
    print("=" * 60)
    print(f"mode        : {mode}")
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
