from __future__ import annotations

"""可直接运行的 Summary Local Demo（非 pytest 断言脚本）。

运行示例：
python summary_module/tests/demo_local_usage.py --backend mock
python summary_module/tests/demo_local_usage.py --backend hf_seq2seq
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

from summary_module import SummaryClient


def build_local_config(base_config: Path, backend: str) -> str:
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
    parser = argparse.ArgumentParser(description="Summary local demo")
    parser.add_argument(
        "--backend",
        choices=["mock", "hf_seq2seq", "hf_causal"],
        default="hf_seq2seq",
        help="本地后端，默认使用小模型后端 hf_seq2seq（配置默认模型 fnlp/bart-base-chinese）",
    )
    parser.add_argument(
        "--text",
        default=(
            "Alice: 大家确认一下Q3目标。\n"
            "Bob: 后端鉴权改造还需要3天。\n"
            "Carol: 前端下周三可以完成联调。\n"
            "Alice: 结论是本周五冻结接口，下周五灰度。"
        ),
    )
    args = parser.parse_args()

    source_text: str = args.text
    backend: str = args.backend

    # 2) 创建摘要模块实例
    base_cfg = Path("summary_module/config/summary.yml")
    temp_cfg_path = build_local_config(base_cfg, backend)
    client = SummaryClient(config_path=temp_cfg_path, mode="local")

    # 3) 传入变量并执行
    result = client.summarize_result(source_text)

    # 4) 打印输出
    print("=" * 60)
    print("Summary Local Demo")
    print("=" * 60)
    print(f"backend     : {backend}")
    print(f"input text  : {source_text}")
    print("-" * 60)
    print(f"summary     : {result.text}")
    print(f"confidence  : {result.confidence:.2f}")
    print(f"latency(ms) : {result.latency_ms}")
    print("=" * 60)


if __name__ == "__main__":
    main()
