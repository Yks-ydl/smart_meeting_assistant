from __future__ import annotations

import re
from collections import defaultdict


SPEAKER_LINE_PATTERN = re.compile(r"^\s*([A-Za-z\u4e00-\u9fa5][\w\-\u4e00-\u9fa5]{0,30})\s*[:：]\s*(.+)$")

AGREE_KEYWORDS = ("同意", "赞成", "支持", "agree", "agreed", "sounds good", "没问题", "可以")
DISAGREE_KEYWORDS = ("不同意", "反对", "冲突", "有问题", "disagree", "can't", "cannot", "不行")
TODO_KEYWORDS = (
    "todo",
    "to do",
    "待办",
    "行动项",
    "需要",
    "请",
    "负责",
    "deadline",
    "截止",
    "目标",
    "next step",
)


def _split_lines(message: str) -> list[str]:
    parts = [line.strip() for line in message.splitlines()]
    return [p for p in parts if p]


def summarize_dialogue(message: str) -> str:
    lines = _split_lines(message)
    if not lines:
        return "未检测到有效对话内容。"

    speaker_utterances: dict[str, list[str]] = defaultdict(list)
    unknown_utterances: list[str] = []
    todos: list[str] = []
    agreements: list[str] = []
    conflicts: list[str] = []

    for line in lines:
        match = SPEAKER_LINE_PATTERN.match(line)
        if match:
            speaker = match.group(1).strip()
            utterance = match.group(2).strip()
            speaker_utterances[speaker].append(utterance)
            scan_text = utterance.lower()
            tagged_line = f"{speaker}: {utterance}"
        else:
            unknown_utterances.append(line)
            scan_text = line.lower()
            tagged_line = line

        if any(k in scan_text for k in TODO_KEYWORDS):
            todos.append(tagged_line)
        if any(k in scan_text for k in AGREE_KEYWORDS):
            agreements.append(tagged_line)
        if any(k in scan_text for k in DISAGREE_KEYWORDS):
            conflicts.append(tagged_line)

    summary_lines: list[str] = ["对话摘要："]

    if speaker_utterances:
        people = "、".join(speaker_utterances.keys())
        summary_lines.append(f"- 参与者：{people}")
    else:
        summary_lines.append("- 参与者：未明确标注说话人")

    if speaker_utterances:
        summary_lines.append("- 观点概览：")
        for speaker, utterances in speaker_utterances.items():
            main_point = "；".join(utterances[:2])
            if len(main_point) > 120:
                main_point = f"{main_point[:117]}..."
            summary_lines.append(f"  - {speaker}：{main_point}")

    if agreements:
        summary_lines.append("- 一致点：")
        for item in agreements[:3]:
            summary_lines.append(f"  - {item}")

    if conflicts:
        summary_lines.append("- 冲突点：")
        for item in conflicts[:3]:
            summary_lines.append(f"  - {item}")

    if todos:
        summary_lines.append("- 待办/目标：")
        for item in todos[:5]:
            summary_lines.append(f"  - {item}")

    if unknown_utterances and not speaker_utterances:
        excerpt = "；".join(unknown_utterances[:2])
        if len(excerpt) > 140:
            excerpt = f"{excerpt[:137]}..."
        summary_lines.append(f"- 主要内容：{excerpt}")

    return "\n".join(summary_lines)
