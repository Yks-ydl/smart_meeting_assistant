#!/usr/bin/env python3
"""手动交互测试翻译 API。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from translation_module import create_translation_client


def _translate_once(client, text: str, src: str, tgt: str) -> None:
    result = client.sync_translate(text, src, tgt)
    print("-" * 60)
    print(f"输入: {text}")
    print(f"输出: {result.text}")
    print(f"置信度: {result.confidence:.2f}")
    print(f"耗时: {result.latency_ms}ms")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manual interactive API translator tester")
    parser.add_argument("--mode", choices=["api", "local"], default="api", help="Translator mode")
    parser.add_argument("--src", default="en", help="Source language")
    parser.add_argument("--tgt", default="zh", help="Target language")
    parser.add_argument("--text", default=None, help="Single-shot text. If omitted, enter interactive mode")
    parser.add_argument("--config", default="config/translation.yml", help="Config path")
    args = parser.parse_args()

    client = create_translation_client(
        src_lang=args.src,
        tgt_lang=args.tgt,
        config_path=args.config,
        mode=args.mode,
    )

    print(f"Mode: {args.mode}")
    print(f"Language: {args.src} -> {args.tgt}")

    if args.text:
        _translate_once(client, args.text, args.src, args.tgt)
        return

    print("进入交互模式：输入文本回车翻译，输入 /exit 退出")
    while True:
        try:
            text = input("\n你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n退出。")
            break

        if not text:
            continue
        if text.lower() in {"/exit", "exit", "quit", "/q"}:
            print("退出。")
            break

        try:
            _translate_once(client, text, args.src, args.tgt)
        except Exception as exc:  # noqa: BLE001
            print(f"翻译失败: {exc}")


if __name__ == "__main__":
    main()
