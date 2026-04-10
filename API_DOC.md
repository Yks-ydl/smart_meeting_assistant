# 智能会议助手 - 接口文档

> 基地址：`http://127.0.0.1:{port}`，各服务启动后可访问 `http://127.0.0.1:{port}/docs` 查看 Swagger 文档。

---

## 服务总览

| 服务 | 端口 | 说明 |
|------|------|------|
| M1 ASR | 8001 | 单轨语言检测 + 语音转文字 |
| M2 Summary | 8002 | 会议纪要生成 |
| M3 Translation | 8003 | 翻译 & 待办提取 |
| M4 Sentiment | 8004 | 情感分析 |
| M5 Gateway | 8000 | WebSocket 网关 |
| M6 Audio Input | 8005 | 本地目录独立音轨处理 |

---

## M1 - ASR 语音识别（:8001）

### POST `/api/v1/asr/transcribe`

处理单条独立音轨。流程为：

1. 音频解码
2. 轻量 VAD
3. 先检测语言
4. 再按检测语言转写
5. BTS 风格后处理

**请求体：**
```json
{
  "audio_base64": "Base64编码后的单轨音频",
  "session_id": "meeting_demo",
  "speaker_hint": "Orangezhi",
  "source_channel": "audioOrangezhi11999480170",
  "chunk_start_time": 0.0,
  "language_hint": null,
  "audio_format": "wav"
}
```

**响应：**
```json
{
  "status": "success",
  "session_id": "meeting_demo",
  "speaker": "Orangezhi",
  "text": "对了，我试一下那个音轨。",
  "language": "zh",
  "source_channel": "audioOrangezhi11999480170",
  "confidence": 0.82,
  "corrected_text": "对了，我试一下那个音轨。",
  "start_time": 2.1,
  "end_time": 5.8,
  "segments": [
    {
      "text": "对了，我试一下那个音轨。",
      "start_time": 2.1,
      "end_time": 5.8,
      "speaker_label": "Orangezhi",
      "confidence": 0.82,
      "source_channel": "audioOrangezhi11999480170",
      "language": "zh",
      "corrected_text": "对了，我试一下那个音轨。"
    }
  ]
}
```

---

## M6 - 音频输入服务（:8005）

### POST `/api/v1/audio/process_directory`

读取本地目录中的多个独立 `.m4a` 文件，并逐轨调用 M1 处理，最后合并 transcript。

**请求体：**
```json
{
  "session_id": "meeting_demo",
  "input_dir": "/Users/orangezhi/Desktop/cityu/NLP/project/audio",
  "glob_pattern": "*.m4a",
  "recursive": false
}
```

**响应：**
```json
{
  "status": "success",
  "session_id": "meeting_demo",
  "mode": "independent_tracks_from_directory",
  "input_dir": "/Users/orangezhi/Desktop/cityu/NLP/project/audio",
  "track_info": [
    {
      "filename": "audioOrangezhi11999480170.m4a",
      "source_channel": "audioOrangezhi11999480170",
      "speaker_label": "Orangezhi",
      "detected_language": "zh"
    }
  ],
  "track_results": [],
  "merged_transcript": [],
  "full_text": "",
  "errors": []
}
```

### GET `/api/v1/audio/status`

查询当前目录处理状态。

### GET `/api/v1/audio/tracks/{session_id}`

获取最近一次目录处理的完整结果，包括：

- `track_info`
- `track_results`
- `merged_transcript`
- `full_text`
- `errors`

---

## M2 - 会议纪要（:8002）

### POST `/api/v1/summary/generate`

**请求体：**
```json
{
  "session_id": "会话ID",
  "text": "完整会议文本"
}
```

---

## M3 - 翻译 & 待办提取（:8003）

### POST `/api/v1/translation/translate`

### POST `/api/v1/translation/extract_actions`

---

## M4 - 情感分析（:8004）

### POST `/api/v1/sentiment/analyze`

分析发言情感和交互信号。

**请求体：**
```json
[
  {
    "text": "发言原始内容（如果存在 corrected_text 则优先分析后者）",
    "corrected_text": "可选：经过 ASR 纠错后的文本内容",
    "start_time": "发言开始时间（浮点数，单位：秒）",
    "end_time": "发言结束时间（浮点数，单位：秒）",
    "speaker_label": "发言人唯一标识/姓名",
    "language": "语种代码：'zh' 代表中文，'en' 代表英文"
  }
]
```

**响应：**
```json
{
  "overall_summary": {
    "total_turns": "本段会议总发言轮次数",
    "dominant_signals": "出现频率最高的前三种交互信号（如：agreement, hesitation）",
    "atmosphere": "整体会议氛围评估：'Positive/Constructive'（积极）或 'Critical/Tense'（紧张）"
  },
  "speaker_profiles": {
    "发言人名称": {
      "participation_count": "该发言人的总发言次数",
      "top_emotion": "该发言人最主流的情感语调",
      "primary_behavior": "该发言人表现最频繁的交互行为（如：confusion, appreciation）",
      "interruption_count": "该发言人的插话/抢话次数"
    }
  },
  "significant_moments": [
    {
      "timestamp": "显著时刻发生的时间范围 [开始, 结束]",
      "speaker": "涉及的发言人",
      "reason": "被标记为显著时刻的原因列表（包含信号类型或 interruption 插话标记）",
      "snippet": "对应的文本片段摘要（前50个字符）"
    }
  ]
}
```

---

## M5 - 网关（:8000）

### GET `/`

返回前端页面。

### WebSocket `/ws/meeting/{session_id}`

当前第一阶段不改协议，语音主标准仍建议通过 M6 目录接口直接使用。
