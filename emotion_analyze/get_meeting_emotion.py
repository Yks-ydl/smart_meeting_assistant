import torch
import json
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
from collections import Counter
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

class MeetingSentimentAnalyzer:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # --- 1. 模型初始化 ---
        print(f"Initializing models on {self.device}...")

        # 中文模型配置
        self.zh_model_name = "Johnson8187/Chinese-Emotion"
        self.zh_tokenizer = AutoTokenizer.from_pretrained(self.zh_model_name)
        self.zh_model = AutoModelForSequenceClassification.from_pretrained(self.zh_model_name).to(self.device)
        self.zh_labels = {
            0: "平淡语气", 1: "关切语调", 2: "开心语调", 3: "愤怒语调",
            4: "悲伤语调", 5: "疑问语调", 6: "惊奇语调", 7: "厌恶语调"
        }

        # 英文模型配置
        self.en_classifier = pipeline(
            task="text-classification",
            model="SamLowe/roberta-base-go_emotions",
            top_k=1,
            device=0 if torch.cuda.is_available() else -1
        )

        # --- 2. 交互特征关键词库 ---
        self.signals_lib = {
            "agreement": ["对", "好", "可以", "没问题", "赞成", "一致", "我同意", "明白", "没意见", "正有此意", "agree",
                          "yes", "exactly", "absolutely", "on the same page", "makes sense", "correct", "definitely"],
            "disagreement": ["不对", "但是", "不妥", "不行", "不太好", "我不这么认为", "有异议", "未必", "反面", "but",
                             "disagree", "no", "not necessarily", "on the contrary", "however", "I doubt", "oppose"],
            "hesitation": ["呃", "那个", "这个", "可能", "大概", "不确定", "让我想想", "或许", "看情况", "视情况而定",
                           "um", "uh", "maybe", "not sure", "let me see", "I guess", "probably", "possibly", "depends"],
            "tension": ["怎么回事", "为什么不", "必须", "绝对", "必须清楚", "简直", "没法做", "不要浪费时间", "够了",
                        "impossible", "nonsense", "ridiculous", "not acceptable", "stop", "waste of time",
                        "why haven't", "must"],
            "appreciation": ["太棒了", "很有启发", "做得好", "感谢", "辛苦了", "有道理", "关键点", "好主意", "great",
                             "excellent", "well done", "appreciate", "thanks", "good point", "brilliant", "spot on"],
            "confusion": ["什么意思", "没跟上", "怎么理解", "再说一遍", "逻辑不对", "没懂", "你的意思是", "confused",
                          "what do you mean", "I don't get it", "can you clarify", "not clear", "pardon"],
            "urgency": ["尽快", "赶紧", "来不及了", "死线", "马上", "优先", "压力", "紧迫", "asap", "deadline",
                        "urgent", "quickly", "immediately", "running out of time", "priority"],
            "passivity": ["随便", "无所谓", "你看着办", "再说吧", "就这样吧", "听你们的", "whatever", "up to you",
                          "doesn't matter", "maybe later", "fine with me"]
        }

    def _get_zh_emotion(self, text):
        inputs = self.zh_tokenizer(text, return_tensors="pt", truncation=True, padding=True).to(self.device)
        with torch.no_grad():
            outputs = self.zh_model(**inputs)
        idx = torch.argmax(outputs.logits).item()
        return self.zh_labels.get(idx, "未知")

    def _get_en_emotion(self, text):
        output = self.en_classifier(text)
        # 返回 top_1 的 label 名称
        return output[0][0]['label']

    def _get_emotion(self, text, language):
        return self._get_zh_emotion(text) if language == "zh" else self._get_en_emotion(text)

    def _extract_signals(self, text):
        text_lower = text.lower()
        found = []
        for category, keywords in self.signals_lib.items():
            if any(kw in text_lower for kw in keywords):
                found.append(category)
        return found if found else ["neutral"]

    def analyze(self, meeting_data):
        """
        主分析函数
        :param meeting_data: List[Dict] 输入的会议片段
        :return: JSON 字符串
        """
        processed_turns = []
        speaker_metrics = {}
        significant_moments = []

        for i, turn in enumerate(meeting_data):
            text = turn.get("corrected_text", turn["text"])
            lang = turn.get("language", "zh")
            speaker = turn["speaker_label"]
            start_t = turn["start_time"]
            end_t = turn["end_time"]

            # 1. 基础情感识别 (根据语言)
            base_emotion = self._get_emotion(text, lang)

            # 2. 交互信号识别
            signals = self._extract_signals(text)

            # 3. 插话检测 (Interruption Detection)
            is_interruption = False
            if i > 0:
                prev_end = meeting_data[i - 1]["end_time"]
                # 如果当前开始时间早于上一句结束时间超过 0.5秒，视为插话
                if start_t < prev_end - 0.5:
                    is_interruption = True

            # 4. 记录显著时刻 (矛盾、紧张或高频插话)
            if any(s in ["disagreement", "tension", "urgency"] for s in signals) or is_interruption:
                significant_moments.append({
                    "timestamp": [start_t, end_t],
                    "speaker": speaker,
                    "reason": signals if not is_interruption else signals + ["interruption"],
                    "snippet": text[:50]
                })

            # 构建单句分析结果
            turn_analysis = {
                "turn_index": i,
                "speaker": speaker,
                "text": text,
                "sentiment": base_emotion,
                "interaction_signals": signals,
                "is_interruption": is_interruption,
                "time_range": [start_t, end_t]
            }
            processed_turns.append(turn_analysis)

            # 更新演讲者统计
            if speaker not in speaker_metrics:
                speaker_metrics[speaker] = {"turns": 0, "emotions": [], "signals": [], "interruptions": 0}

            speaker_metrics[speaker]["turns"] += 1
            speaker_metrics[speaker]["emotions"].append(base_emotion)
            speaker_metrics[speaker]["signals"].extend(signals)
            if is_interruption: speaker_metrics[speaker]["interruptions"] += 1

        # 5. 整体汇总逻辑
        all_signals = [s for t in processed_turns for s in t["interaction_signals"]]
        signal_counts = Counter(all_signals)

        final_output = {
            "overall_summary": {
                "total_turns": len(meeting_data),
                "dominant_signals": signal_counts.most_common(3),
                "atmosphere": "Positive/Constructive" if signal_counts["agreement"] > signal_counts[
                    "disagreement"] else "Critical/Tense"
            },
            "speaker_profiles": {
                name: {
                    "participation_count": stats["turns"],
                    "top_emotion": Counter(stats["emotions"]).most_common(1)[0][0] if stats["emotions"] else "N/A",
                    "primary_behavior": Counter(stats["signals"]).most_common(1)[0][0] if stats[
                        "signals"] else "Neutral",
                    "interruption_count": stats["interruptions"]
                } for name, stats in speaker_metrics.items()
            },
            "significant_moments": significant_moments,
            # "detailed_analysis": processed_turns
        }

        return json.dumps(final_output, ensure_ascii=False, indent=2)


# --- 使用示例 ---
if __name__ == "__main__":
    raw_data = [
        {
            "text": "Hello,可以听,对了,我试一下那个英诡,就我上次也说了,就是那个,呃,就不同英诡接近,才会有不同人的名字,然后才更好总结吗?",
            "start_time": 2.1, "end_time": 30.0, "speaker_label": "Orangezhi", "language": "zh"
        },
        {
            "text": "哈喽,可以聽得見,英国,那就要求五個人都去按照我們這個System等",
            "start_time": 25.0, "end_time": 45.0, "speaker_label": "YANGKaisen", "language": "zh"
        },
        {
            "text": "I am not convinced this will work, it seems too complex.",
            "start_time": 46.0, "end_time": 52.0, "speaker_label": "Orangezhi", "language": "en"
        }
    ]

    analyzer = MeetingSentimentAnalyzer()
    json_result = analyzer.analyze(raw_data)
    print(json_result)