from collections import Counter

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="M4 - Sentiment & Engagement Analysis Service")


class Utterance(BaseModel):
    text: str
    corrected_text: str | None = None
    start_time: float
    end_time: float
    speaker_label: str
    language: str = "zh"


SIGNAL_KEYWORDS = {
    "agreement": ["同意", "赞成", "可以", "没问题", "agree", "exactly", "makes sense"],
    "disagreement": ["不对", "反对", "不太行", "different view", "disagree", "however"],
    "hesitation": ["可能", "不确定", "再想想", "maybe", "not sure", "probably"],
    "urgency": ["尽快", "马上", "紧急", "deadline", "urgent", "asap"],
    "tension": ["必须", "不接受", "不合理", "ridiculous", "impossible"],
    "appreciation": ["感谢", "辛苦", "好主意", "thanks", "great", "well done"],
}

POSITIVE_HINTS = ["好", "赞", "感谢", "优秀", "great", "good", "excellent", "thanks"]
NEGATIVE_HINTS = ["差", "糟", "不行", "问题", "bad", "fail", "issue", "worse"]


def detect_signals(text: str) -> list[str]:
    lowered = text.lower()
    found: list[str] = []
    for signal, keywords in SIGNAL_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            found.append(signal)
    return found or ["neutral"]


def detect_emotion(text: str) -> str:
    lowered = text.lower()
    positive_hits = sum(1 for keyword in POSITIVE_HINTS if keyword in lowered)
    negative_hits = sum(1 for keyword in NEGATIVE_HINTS if keyword in lowered)

    if positive_hits > negative_hits:
        return "positive"
    if negative_hits > positive_hits:
        return "negative"
    return "neutral"


def build_empty_report() -> dict:
    return {
        "overall_summary": {
            "total_turns": 0,
            "dominant_signals": [],
            "atmosphere": "Positive/Constructive",
        },
        "speaker_profiles": {},
        "significant_moments": [],
    }


@app.post("/api/v1/sentiment/analyze")
async def analyze_sentiment(utterances: list[Utterance]):
    """会议级情感与交互信号分析，输出结构对齐 API 文档中的 M4 响应。"""
    if not utterances:
        return build_empty_report()

    speaker_metrics: dict[str, dict] = {}
    significant_moments: list[dict] = []
    all_signals: list[str] = []

    previous_end_time = 0.0
    for turn in utterances:
        text = (turn.corrected_text or turn.text or "").strip()
        if not text:
            continue

        signals = detect_signals(text)
        emotion = detect_emotion(text)
        all_signals.extend(signals)

        is_interruption = turn.start_time < (previous_end_time - 0.5)
        previous_end_time = max(previous_end_time, turn.end_time)

        if any(signal in {"disagreement", "tension", "urgency"} for signal in signals) or is_interruption:
            reasons = list(signals)
            if is_interruption:
                reasons.append("interruption")
            significant_moments.append(
                {
                    "timestamp": [turn.start_time, turn.end_time],
                    "speaker": turn.speaker_label,
                    "reason": reasons,
                    "snippet": text[:50],
                }
            )

        if turn.speaker_label not in speaker_metrics:
            speaker_metrics[turn.speaker_label] = {
                "turns": 0,
                "emotions": [],
                "signals": [],
                "interruptions": 0,
            }

        speaker_metrics[turn.speaker_label]["turns"] += 1
        speaker_metrics[turn.speaker_label]["emotions"].append(emotion)
        speaker_metrics[turn.speaker_label]["signals"].extend(signals)
        if is_interruption:
            speaker_metrics[turn.speaker_label]["interruptions"] += 1

    if not speaker_metrics:
        return build_empty_report()

    signal_counts = Counter(all_signals)
    dominant_signals = [signal for signal, _count in signal_counts.most_common(3)]

    agreement_count = signal_counts.get("agreement", 0) + signal_counts.get("appreciation", 0)
    critical_count = signal_counts.get("disagreement", 0) + signal_counts.get("tension", 0)
    atmosphere = "Positive/Constructive" if agreement_count >= critical_count else "Critical/Tense"

    speaker_profiles = {}
    for speaker, stats in speaker_metrics.items():
        top_emotion = Counter(stats["emotions"]).most_common(1)[0][0] if stats["emotions"] else "neutral"
        primary_behavior = Counter(stats["signals"]).most_common(1)[0][0] if stats["signals"] else "neutral"
        speaker_profiles[speaker] = {
            "participation_count": stats["turns"],
            "top_emotion": top_emotion,
            "primary_behavior": primary_behavior,
            "interruption_count": stats["interruptions"],
        }

    return {
        "overall_summary": {
            "total_turns": sum(metrics["turns"] for metrics in speaker_metrics.values()),
            "dominant_signals": dominant_signals,
            "atmosphere": atmosphere,
        },
        "speaker_profiles": speaker_profiles,
        "significant_moments": significant_moments,
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)
