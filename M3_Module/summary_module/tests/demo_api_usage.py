from __future__ import annotations

"""可直接运行的 Summary API Demo（非 pytest 断言脚本）。

运行：
python summary_module/tests/demo_api_usage.py
"""

import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from summary_module import SummaryClient


def main() -> None:
    # 1) 输入变量声明
    config_path: str = "summary_module/config/summary.yml"
    mode: str = "api"
    source_text: str = (
        "Alice: 我们本周要冻结接口，目标是下周五灰度。\n"
        "Bob: 后端鉴权改造预计三天完成。\n"
        "Carol: 前端确认下周三完成联调。\n"
        "David: 风险是海外节点延迟，建议先10%灰度。"
    )

    # 2) 创建摘要模块实例
    client = SummaryClient(config_path=config_path, mode=mode)

    # 3) 传入变量并执行
    result = client.summarize_result(source_text)

    # 4) 打印输出
    print("=" * 60)
    print("Summary API Demo")
    print("=" * 60)
    print(f"mode        : {mode}")
    print(f"input text  : {source_text}")
    print("-" * 60)
    print(f"summary     : {result.text}")
    print(f"confidence  : {result.confidence:.2f}")
    print(f"latency(ms) : {result.latency_ms}")
    print("=" * 60)


if __name__ == "__main__":
    main()
