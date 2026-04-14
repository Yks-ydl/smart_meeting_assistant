from fastapi import FastAPI
from pydantic import BaseModel
import sys
import os
import uvicorn
import re

# 将项目根目录加入 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.llm_utils import call_llm
from core.chinese_utils import normalize_simplified_chinese_text

app = FastAPI(title="M3 - Translation & Action Extraction Service")

class TextContent(BaseModel):
    session_id: str
    text: str
    target_lang: str = "en"  # 目标语言，默认英文

@app.post("/api/v1/translation/translate")
async def translate_text(content: TextContent):
    """
    多语言实时机器翻译 (MT)
    """
    target_lang = content.target_lang.lower().split('-')[0].split('_')[0]
    normalized_target = "简体中文" if target_lang == "zh" else content.target_lang
    system_prompt = (
        f"你是一个专业的同声传译员。请将以下文本翻译成{normalized_target}。"
        "如果输出中文，请统一使用简体中文。只输出翻译结果。"
    )
    
    translated_text = normalize_simplified_chinese_text(
        call_llm(system_prompt=system_prompt, user_prompt=content.text)
    )
        
    return {
        "status": "success",
        "session_id": content.session_id,
        "translated_text": translated_text
    }


# 用于解析行动项的正则表达式模式
ACTION_ITEM_PATTERN = re.compile(
    r'^\s*[-*•]\s*(?:\[.*?\]\s*)?(?:(?P<assignee>[^：:]+)[:：]\s*)?(?P<task>.+?)(?:\s*(?:截止|deadline|by|before|在)\s*(?P<deadline>[^\n]+))?$',
    re.MULTILINE | re.IGNORECASE
)


@app.post("/api/v1/translation/extract_actions")
async def extract_actions(content: TextContent):
    """
    上下文感知段落摘要事项提取 (Action Items Extraction)
    提取会议中的待办事项
    """
    system_prompt = """你是一个专业的项目经理助手。请从以下会议记录中提取具体的待办事项（Action Items）。

提取要求：
1. 找出所有需要执行的任务、行动或跟进事项
2. 识别任务的负责人（如果有提到）
3. 识别任务的截止日期（如果有提到）
4. 如果没有待办事项，请明确返回"无待办事项"

输出格式要求：
- 每个行动项单独一行
- 格式：- [负责人]: 任务描述 (截止日期)
- 如果负责人或截止日期未知，可以省略
- 示例：
  - 张三: 完成项目文档 (周五前)
  - 李四: 安排下次会议
  - 王五: 准备演示材料 (明天)

请以 Markdown 列表形式输出所有行动项。"""

    actions_result = call_llm(
        system_prompt=system_prompt + "\n\n如果输出中文，请统一使用简体中文。",
        user_prompt=normalize_simplified_chinese_text(content.text),
    )

    # 尝试解析行动项为结构化数据
    actions_result = normalize_simplified_chinese_text(actions_result)
    parsed_actions = parse_action_items(actions_result)

    return {
        "status": "success",
        "session_id": content.session_id,
        "action_items": actions_result,
        "parsed_actions": parsed_actions
    }


def parse_action_items(text: str) -> list[dict]:
    """
    解析行动项文本为结构化数据
    """
    actions = []
    lines = text.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 检查是否是列表项（以 -, *, • 或数字开头）
        if not re.match(r'^\s*[-*•\d]', line):
            continue

        # 移除列表标记
        cleaned = re.sub(r'^\s*[-*•]\s*', '', line)
        cleaned = re.sub(r'^\s*\d+\.\s*', '', line)

        if not cleaned or cleaned.lower() in ['无', '无待办事项', 'none', 'no action items', 'n/a']:
            continue

        # 尝试解析负责人和任务
        assignee = None
        task = cleaned
        deadline = None

        # 匹配 "负责人: 任务" 或 "负责人：任务" 格式
        match = re.match(r'^([^：:]+)[:：]\s*(.+)$', cleaned)
        if match:
            potential_assignee = match.group(1).strip()
            potential_task = match.group(2).strip()

            # 过滤掉非人名的开头（如 "任务"、"TODO" 等）
            if not re.match(r'^(任务|todo|action|item|待办)', potential_assignee.lower()):
                assignee = potential_assignee
                task = potential_task

        # 尝试提取截止日期
        deadline_patterns = [
            r'(?:截止|deadline|by|before|在)\s*[:：]?\s*([^()（）]+)',
            r'\(([^)]+)\)$',  # 括号内的内容
            r'（([^）]+)）$',  # 中文括号内的内容
        ]

        for pattern in deadline_patterns:
            deadline_match = re.search(pattern, task, re.IGNORECASE)
            if deadline_match:
                potential_deadline = deadline_match.group(1).strip()
                # 过滤掉非日期的内容
                if re.search(r'\d|今天|明天|后天|周|星期|月|号|日|前|后', potential_deadline):
                    deadline = potential_deadline
                    # 从任务中移除截止日期部分
                    task = re.sub(r'\s*' + re.escape(deadline_match.group(0)) + r'$', '', task)
                    task = task.strip()
                    break

        if task:
            actions.append({
                "task": task,
                "assignee": assignee,
                "deadline": deadline
            })

    return actions


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
