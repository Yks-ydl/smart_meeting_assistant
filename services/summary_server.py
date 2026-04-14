"""
M2 - 智能会议纪要生成服务 (混合架构)

采用 Reconstruct-before-Summarize 架构：
  阶段一：本地预训练模型（BART/T5）进行初步摘要提取
  阶段二：大模型 API 进行结构化精炼润色
支持三种模式对比实验 + ROUGE 评估
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List
import sys
import os
import uvicorn
import traceback

# 将项目根目录加入 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.chinese_utils import normalize_simplified_chinese_text
from core.llm_utils import call_llm
from core.text_utils import (
    clean_meeting_text,
    split_text_by_length,
    split_text_by_sentences,
    merge_summaries,
    format_structured_summary,
)

app = FastAPI(title="M2 - Smart Summarization Service (Hybrid)")

# ──────────────────────────────────────────────
# 本地摘要模型加载（启动时初始化）
# ──────────────────────────────────────────────
local_model = None
local_tokenizer = None
LOCAL_MODEL_NAME = os.getenv("SUMMARY_MODEL", "fnlp/bart-base-chinese")
LOCAL_MAX_INPUT_LENGTH = 512   # 本地模型最大输入 token 数
LOCAL_MAX_OUTPUT_LENGTH = 200  # 本地模型最大输出 token 数

def load_local_model():
    """加载本地摘要模型，失败时降级为纯 LLM 模式"""
    global local_model, local_tokenizer
    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        print(f"[M2] 正在加载本地摘要模型: {LOCAL_MODEL_NAME} ...")
        local_tokenizer = AutoTokenizer.from_pretrained(LOCAL_MODEL_NAME)
        local_model = AutoModelForSeq2SeqLM.from_pretrained(LOCAL_MODEL_NAME)
        local_model.eval()
        print(f"[M2] 本地摘要模型加载完成: {LOCAL_MODEL_NAME}")
    except Exception as e:
        print(f"[M2] 本地摘要模型加载失败，将降级为纯 LLM 模式: {e}")
        local_model = None
        local_tokenizer = None

# 启动时尝试加载
load_local_model()

# ──────────────────────────────────────────────
# 请求/响应模型
# ──────────────────────────────────────────────

class MeetingContent(BaseModel):
    session_id: str
    text: str

class EvaluateRequest(BaseModel):
    reference: str            # 参考摘要
    hypothesis: str           # 生成摘要

class EvaluateResponse(BaseModel):
    rouge_1: dict
    rouge_2: dict
    rouge_l: dict

# ──────────────────────────────────────────────
# 核心摘要函数
# ──────────────────────────────────────────────

def _local_summarize(text: str) -> str:
    """
    使用本地模型生成摘要。
    对超长文本进行分段处理，分别摘要后合并。
    """
    if local_model is None or local_tokenizer is None:
        return ""

    import torch

    cleaned = clean_meeting_text(text)
    segments = split_text_by_length(cleaned, max_length=LOCAL_MAX_INPUT_LENGTH, overlap=50)

    summaries = []
    for seg in segments:
        try:
            inputs = local_tokenizer(
                seg,
                return_tensors="pt",
                max_length=LOCAL_MAX_INPUT_LENGTH,
                truncation=True,
                padding=True,
            )
            with torch.no_grad():
                outputs = local_model.generate(
                    **inputs,
                    max_length=LOCAL_MAX_OUTPUT_LENGTH,
                    num_beams=4,
                    length_penalty=1.0,
                    early_stopping=True,
                )
            decoded = local_tokenizer.decode(outputs[0], skip_special_tokens=True)
            if decoded.strip():
                summaries.append(decoded.strip())
        except Exception as e:
            print(f"[M2] 本地模型推理段落失败: {e}")
            continue

    return merge_summaries(summaries)


def _llm_summarize(text: str) -> str:
    """
    仅使用大模型 API 生成摘要（保留原有逻辑，增强 Prompt）
    """
    cleaned = clean_meeting_text(text)

    system_prompt = """你是一个专业的智能会议助手。你的任务是对输入的会议记录进行整理，生成结构清晰的会议纪要。

如果输出中文，请统一使用简体中文。

请按以下四个板块输出：

## 会议主旨
（一句话概括本次会议的核心议题和目的）

## 核心要点
（用编号列表罗列会议中讨论的关键内容，每条不超过两句话）

## 决策事项
（列出会议中已经达成共识或做出决定的事项，如果没有则写"无"）

## 待跟进问题
（列出需要后续跟进或尚未解决的问题，如果没有则写"无"）"""

    user_prompt = f"请对以下会议记录进行总结：\n\n{cleaned}"

    return call_llm(system_prompt=system_prompt, user_prompt=user_prompt)


def _hybrid_summarize(text: str) -> str:
    """
    混合摘要：本地模型初步提取 → 大模型精炼润色
    """
    # 阶段一：本地模型初步摘要
    local_summary = _local_summarize(text)

    # 如果本地模型不可用或输出为空，直接走纯 LLM 路径
    if not local_summary:
        print("[M2] 本地模型无输出，降级为纯 LLM 摘要")
        return _llm_summarize(text)

    # 阶段二：大模型精炼
    cleaned_original = clean_meeting_text(text)

    system_prompt = """你是一个专业的智能会议助手。下面会提供两段内容：
1. 原始会议记录
2. AI 助手生成的初步摘要

请基于原始会议记录，参考初步摘要，生成一份更准确、更完整、结构清晰的最终会议纪要。

如果输出中文，请统一使用简体中文。

请按以下四个板块输出：

## 会议主旨
（一句话概括本次会议的核心议题和目的）

## 核心要点
（用编号列表罗列会议中讨论的关键内容，每条不超过两句话）

## 决策事项
（列出会议中已经达成共识或做出决定的事项，如果没有则写"无"）

## 待跟进问题
（列出需要后续跟进或尚未解决的问题，如果没有则写"无"）"""

    user_prompt = f"""### 原始会议记录
{cleaned_original}

### AI 初步摘要
{local_summary}

请生成最终会议纪要："""

    return call_llm(system_prompt=system_prompt, user_prompt=user_prompt)


# ──────────────────────────────────────────────
# API 端点
# ──────────────────────────────────────────────

@app.post("/api/v1/summary/generate")
async def generate_summary(content: MeetingContent):
    """
    混合摘要生成（默认模式）
    阶段一：本地模型压缩提取
    阶段二：大模型精炼润色与结构化
    """
    try:
        summary_text = normalize_simplified_chinese_text(_hybrid_summarize(content.text))
        structured = format_structured_summary(summary_text)

        return {
            "status": "success",
            "session_id": content.session_id,
            "summary": summary_text,
            "structured": structured,
            "mode": "hybrid" if local_model is not None else "llm_fallback",
        }
    except Exception as e:
        traceback.print_exc()
        return {
            "status": "error",
            "session_id": content.session_id,
            "summary": f"摘要生成失败: {str(e)}",
            "mode": "error",
        }


@app.post("/api/v1/summary/generate_local")
async def generate_summary_local(content: MeetingContent):
    """
    仅本地模型摘要（对比实验用）
    """
    if local_model is None:
        return {
            "status": "error",
            "session_id": content.session_id,
            "summary": "本地模型未加载，无法使用此端点",
            "mode": "local",
        }

    try:
        summary_text = _local_summarize(content.text)
        return {
            "status": "success",
            "session_id": content.session_id,
            "summary": summary_text,
            "mode": "local",
        }
    except Exception as e:
        traceback.print_exc()
        return {
            "status": "error",
            "session_id": content.session_id,
            "summary": f"本地摘要失败: {str(e)}",
            "mode": "local",
        }


@app.post("/api/v1/summary/generate_llm")
async def generate_summary_llm(content: MeetingContent):
    """
    仅大模型 API 摘要（对比实验用）
    """
    try:
        summary_text = _llm_summarize(content.text)
        return {
            "status": "success",
            "session_id": content.session_id,
            "summary": summary_text,
            "mode": "llm",
        }
    except Exception as e:
        traceback.print_exc()
        return {
            "status": "error",
            "session_id": content.session_id,
            "summary": f"LLM 摘要失败: {str(e)}",
            "mode": "llm",
        }


@app.post("/api/v1/summary/evaluate")
async def evaluate_summary(req: EvaluateRequest):
    """
    ROUGE 评估端点
    计算生成摘要与参考摘要之间的 ROUGE-1 / ROUGE-2 / ROUGE-L 分数
    """
    try:
        import jieba
        from rouge_chinese import Rouge

        # 中文 ROUGE 需要先分词
        ref_tokens = ' '.join(jieba.cut(req.reference))
        hyp_tokens = ' '.join(jieba.cut(req.hypothesis))

        rouge = Rouge()
        scores = rouge.get_scores(hyp_tokens, ref_tokens)[0]

        return {
            "status": "success",
            "rouge_1": scores["rouge-1"],
            "rouge_2": scores["rouge-2"],
            "rouge_l": scores["rouge-l"],
        }
    except ImportError:
        return {
            "status": "error",
            "message": "请安装 rouge-chinese 和 jieba: pip install rouge-chinese jieba",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"评估失败: {str(e)}",
        }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "M2 - Summary",
        "local_model_loaded": local_model is not None,
        "local_model_name": LOCAL_MODEL_NAME if local_model else None,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
