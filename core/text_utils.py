"""
文本处理工具模块
提供会议记录的预处理、分段、后处理等功能
"""

import re
from typing import List


def clean_meeting_text(text: str) -> str:
    """
    清洗会议记录文本：
    - 去除多余空行和空白
    - 统一标点符号格式
    - 去除时间戳等冗余标记
    """
    # 去除常见时间戳格式 如 [00:01:23] 或 (00:01:23)
    text = re.sub(r'[\[\(]\d{1,2}:\d{2}(:\d{2})?[\]\)]', '', text)
    # 去除连续空行，保留最多一个换行
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 去除行首行尾多余空白
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    # 去除首尾空白
    text = text.strip()
    return text


def split_text_by_length(text: str, max_length: int = 512, overlap: int = 50) -> List[str]:
    """
    按字符长度将长文本切分为多个片段，支持重叠以保留上下文。
    适用于本地摘要模型的输入限制。

    Args:
        text: 待切分文本
        max_length: 每个片段的最大字符数
        overlap: 相邻片段的重叠字符数

    Returns:
        切分后的文本片段列表
    """
    if len(text) <= max_length:
        return [text]

    segments = []
    start = 0
    while start < len(text):
        end = start + max_length

        # 尝试在句号、问号、感叹号、换行处截断，避免切断句子
        if end < len(text):
            # 在 [end-100, end] 范围内寻找最后一个句子结束符
            search_start = max(start, end - 100)
            last_break = -1
            for delimiter in ['。', '！', '？', '\n', '；', '.', '!', '?']:
                pos = text.rfind(delimiter, search_start, end)
                if pos > last_break:
                    last_break = pos

            if last_break > start:
                end = last_break + 1  # 包含分隔符

        segment = text[start:end].strip()
        if segment:
            segments.append(segment)

        # 下一段起始位置，减去重叠部分
        start = end - overlap if end < len(text) else end

    return segments


def split_text_by_sentences(text: str, max_sentences: int = 20) -> List[str]:
    """
    按句子数量切分文本，适用于对话式会议记录。

    Args:
        text: 待切分文本
        max_sentences: 每个片段最大句子数

    Returns:
        切分后的文本片段列表
    """
    # 按换行分割（会议记录通常一行一句发言）
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    if len(lines) <= max_sentences:
        return [text]

    segments = []
    for i in range(0, len(lines), max_sentences):
        segment = '\n'.join(lines[i:i + max_sentences])
        segments.append(segment)

    return segments


def merge_summaries(summaries: List[str]) -> str:
    """
    合并多个分段摘要为一个统一的中间摘要。
    去除重复内容，保持逻辑连贯。

    Args:
        summaries: 各分段的摘要列表

    Returns:
        合并后的摘要文本
    """
    if not summaries:
        return ""
    if len(summaries) == 1:
        return summaries[0]

    # 合并所有摘要，用换行分隔
    merged = '\n'.join(summaries)

    # 简单去重：按句子拆分，去除完全重复的句子
    seen = set()
    unique_lines = []
    for line in merged.split('\n'):
        line = line.strip()
        if line and line not in seen:
            seen.add(line)
            unique_lines.append(line)

    return '\n'.join(unique_lines)


def format_structured_summary(raw_summary: str) -> dict:
    """
    将原始摘要文本解析为结构化格式。
    尝试识别「会议主旨」「核心要点」「决策事项」「待跟进问题」等板块。

    Args:
        raw_summary: 原始摘要文本

    Returns:
        结构化摘要字典
    """
    result = {
        "main_topic": "",
        "key_points": [],
        "decisions": [],
        "follow_ups": []
    }

    # 尝试按标题分块解析
    current_section = "main_topic"
    current_content = []

    for line in raw_summary.split('\n'):
        line = line.strip()
        if not line:
            continue

        # 检测板块标题
        lower_line = line.lower()
        if any(kw in lower_line for kw in ['会议主旨', '主旨', '概述', '总结', 'overview', 'summary']):
            if current_content:
                _assign_section(result, current_section, current_content)
                current_content = []
            current_section = "main_topic"
            # 如果标题行本身包含内容（如 "会议主旨：xxx"）
            content_after_colon = _extract_after_colon(line)
            if content_after_colon:
                current_content.append(content_after_colon)
            continue
        elif any(kw in lower_line for kw in ['核心要点', '要点', '关键点', 'key points']):
            if current_content:
                _assign_section(result, current_section, current_content)
                current_content = []
            current_section = "key_points"
            continue
        elif any(kw in lower_line for kw in ['决策', '决定', 'decisions']):
            if current_content:
                _assign_section(result, current_section, current_content)
                current_content = []
            current_section = "decisions"
            continue
        elif any(kw in lower_line for kw in ['跟进', '待办', '后续', 'follow', 'action']):
            if current_content:
                _assign_section(result, current_section, current_content)
                current_content = []
            current_section = "follow_ups"
            continue

        # 去除列表标记
        clean_line = re.sub(r'^[\d\-\*\•\.、]+\s*', '', line).strip()
        if clean_line:
            current_content.append(clean_line)

    # 处理最后一个分块
    if current_content:
        _assign_section(result, current_section, current_content)

    return result


def _assign_section(result: dict, section: str, content: list):
    """将内容分配到对应板块"""
    if section == "main_topic":
        result["main_topic"] = '\n'.join(content)
    elif section in ("key_points", "decisions", "follow_ups"):
        result[section].extend(content)


def _extract_after_colon(line: str) -> str:
    """提取冒号后的内容"""
    for sep in ['：', ':']:
        if sep in line:
            return line.split(sep, 1)[1].strip()
    return ""
