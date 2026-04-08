from __future__ import annotations

"""根目录可直接运行的双模块 Demo。

目标：
1) 演示如何 import 两个模块
2) 假定一段真实会议 message
3) 实例化 Translation + Summary 两个模块
4) 传入变量并打印输出结果

运行：
python demo_meeting_pipeline.py
"""

from pathlib import Path
from typing import TypedDict

from summary_module import create_summary_client
from translation_module import create_translation_client


class MeetingItem(TypedDict):
    user: str
    text: str


def build_summary_message(items: list[MeetingItem]) -> str:
    """将结构化会议条目拼接为摘要模块输入文本。"""
    return "\n".join(f"{item['user']}: {item['text']}" for item in items)


def translate_meeting_items(
    items: list[MeetingItem],
    translator,
    src_lang: str,
    tgt_lang: str,
) -> tuple[list[MeetingItem], int, float]:
    """逐条翻译 meeting item 的 text 字段，并返回聚合统计。"""
    translated_items: list[MeetingItem] = []
    total_latency_ms = 0
    confidence_sum = 0.0

    for item in items:
        result = translator.translate_result(
            text=item["text"],
            src_lang=src_lang,
            tgt_lang=tgt_lang,
        )
        translated_items.append({"user": item["user"], "text": result.text})
        total_latency_ms += result.latency_ms
        confidence_sum += result.confidence

    avg_confidence = confidence_sum / len(items) if items else 0.0
    return translated_items, total_latency_ms, avg_confidence


def main() -> None:
    # -----------------------------------------------------------------
    # 1) 输入变量声明（模拟真实会议场景）
    # -----------------------------------------------------------------
    meeting_items: list[MeetingItem] = [
        {"user": "Alice", "text": "大家下午好，我们今天要确定Q3上线范围和截止时间。"},
        {"user": "Bob", "text": "后端接口已经完成70%，但鉴权改造还需要3天。"},
        {"user": "Carol", "text": "前端这边如果接口本周冻结，我们可以在下周三完成联调。"},
        {"user": "David", "text": "风险点是海外节点延迟，建议先灰度到10%用户。"},
        {"user": "Alice", "text": "好，那我们达成共识：本周五冻结接口，下周三联调，下周五灰度发布。"},
        {"user": "Alice", "text": "Action Items：Bob负责鉴权收尾；Carol负责联调计划；David负责灰度与监控看板。"},
    ]

    meeting_message: str = build_summary_message(meeting_items)

    translation_src_lang: str = "zh"
    translation_tgt_lang: str = "en"

    translation_config_path: str = "translation_module/config/translation.yml"
    summary_config_path: str = "summary_module/config/summary.yml"

    translation_mode: str = "local"  # api | local
    summary_mode: str = "local"        # api | local（当前建议用 api，local 效果不好)

    # -----------------------------------------------------------------
    # 2) 实例化两个模块
    # -----------------------------------------------------------------
    translator = create_translation_client(
        src_lang=translation_src_lang,
        tgt_lang=translation_tgt_lang,
        config_path=translation_config_path,
        mode=translation_mode,
    )

    summarizer = create_summary_client(
        config_path=summary_config_path,
        mode=summary_mode,
    )

    # -----------------------------------------------------------------
    # 3) 执行两个模块功能
    # -----------------------------------------------------------------
    # 3.1 会议摘要
    summary_result = summarizer.summarize_result(meeting_message)

    # 3.2 逐条翻译会议内容（仅翻译每个 item 的 text）
    translated_items, total_latency_ms, avg_confidence = translate_meeting_items(
        items=meeting_items,
        translator=translator,
        src_lang=translation_src_lang,
        tgt_lang=translation_tgt_lang,
    )

    # -----------------------------------------------------------------
    # 4) 打印结果
    # -----------------------------------------------------------------
    print("=" * 80)
    print("Smart Meeting Assistant Demo (Summary + Translation)")
    print("=" * 80)
    print(f"Project Root: {Path(__file__).resolve().parent}")
    print()

    print("[Input Meeting Items]")
    print("-" * 80)
    for item in meeting_items:
        print(f"{item['user']}: {item['text']}")
    print()

    print("[Summary Output]")
    print("-" * 80)
    print(summary_result.text)
    print(f"(confidence={summary_result.confidence:.2f}, latency={summary_result.latency_ms}ms)")
    print()

    print("[Translation Output by Meeting Item: zh -> en]")
    print("-" * 80)
    for item in translated_items:
        print(f"{item['user']}: {item['text']}")
    print(f"(avg_confidence={avg_confidence:.2f}, total_latency={total_latency_ms}ms)")
    print("=" * 80)


if __name__ == "__main__":
    main()
