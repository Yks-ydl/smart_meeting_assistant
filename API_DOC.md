# 智能会议助手 - 接口文档

> 基地址：`http://127.0.0.1:{port}`，各服务启动后可访问 `http://127.0.0.1:{port}/docs` 查看 Swagger 交互文档。

---

## 服务总览

| 服务 | 端口 | 说明 |
|------|------|------|
| M1 ASR | 8001 | 语音转文字 |
| M2 Summary | 8002 | 会议纪要生成（混合架构） |
| M3 Translation | 8003 | 翻译 & 待办提取 |
| M4 Sentiment | 8004 | 情感分析 |
| M5 Gateway | 8000 | WebSocket 网关 & 前端 |
| M6 Audio Input | 8005 | 音频采集与分发 |

---

## M1 - ASR 语音识别（:8001）

### POST `/api/v1/asr/transcribe`

语音转文字。无真实音频时自动使用 LLM Mock。

**请求体：**
```json
{
  "audio_base64": "Base64编码的音频数据",
  "session_id": "会话ID"
}
```

**响应：**
```json
{
  "status": "success",
  "session_id": "...",
  "speaker": "Speaker_1",
  "text": "转录文本内容"
}
```

---

## M2 - 会议纪要（:8002）

### POST `/api/v1/summary/generate`

混合摘要（本地模型初步提取 + 大模型精炼），默认模式。

**请求体：**
```json
{
  "session_id": "会话ID",
  "text": "完整会议文本"
}
```

**响应：**
```json
{
  "status": "success",
  "session_id": "...",
  "summary": "纪要文本",
  "structured": {
    "main_topic": "会议主旨",
    "key_points": ["要点1", "要点2"],
    "decisions": ["决策1"],
    "follow_ups": ["待跟进1"]
  },
  "mode": "hybrid"
}
```

### POST `/api/v1/summary/generate_local`

仅本地模型摘要（对比实验用）。请求/响应格式同上，`mode` 为 `"local"`。

### POST `/api/v1/summary/generate_llm`

仅大模型 API 摘要（对比实验用）。请求/响应格式同上，`mode` 为 `"llm"`。

### POST `/api/v1/summary/evaluate`

ROUGE 指标评估。

**请求体：**
```json
{
  "reference": "参考摘要",
  "hypothesis": "生成摘要"
}
```

**响应：**
```json
{
  "status": "success",
  "rouge_1": { "r": 0.8, "p": 0.7, "f": 0.75 },
  "rouge_2": { "r": 0.5, "p": 0.4, "f": 0.44 },
  "rouge_l": { "r": 0.7, "p": 0.6, "f": 0.65 }
}
```

---

## M3 - 翻译 & 待办提取（:8003）

### POST `/api/v1/translation/translate`

多语言翻译。

**请求体：**
```json
{
  "session_id": "会话ID",
  "text": "待翻译文本",
  "target_lang": "en"
}
```

**响应：**
```json
{
  "status": "success",
  "session_id": "...",
  "translated_text": "翻译结果"
}
```

### POST `/api/v1/translation/extract_actions`

提取待办事项。

**请求体：**
```json
{
  "session_id": "会话ID",
  "text": "会议记录文本"
}
```

**响应：**
```json
{
  "status": "success",
  "session_id": "...",
  "action_items": "- 待办1\n- 待办2"
}
```

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

会议实时通道。

**客户端发送消息：**

| type | 字段 | 说明 |
|------|------|------|
| `audio_chunk` | `data`: Base64 音频 | 发送音频片段，触发 ASR → 情感 + 翻译 |
| `end_meeting` | `full_text`: 完整文本 | 结束会议，触发 摘要 + 待办提取 |

**服务端推送消息：**

| type | 数据 | 说明 |
|------|------|------|
| `asr_result` | `{speaker, text}` | 实时转录结果 |
| `analysis_result` | `{sentiment, translation}` | 情感 + 翻译结果 |
| `meeting_end_report` | `{summary, actions}` | 会议纪要 + 待办事项 |

---

## M6 - 音频输入服务（:8005）

### POST `/api/v1/audio/start_capture`

**模式一**：启动双人实时采集（麦克风 + 扬声器 loopback）。

**请求体：**
```json
{
  "session_id": "会话ID",
  "mic_device_index": null,
  "loopback_device_index": null,
  "duration_sec": null
}
```

所有字段除 `session_id` 外均可选，`null` 表示使用默认值/持续录制。

### POST `/api/v1/audio/stop_capture`

停止实时采集，返回所有转录结果。

**请求体：**
```json
{ "session_id": "会话ID" }
```

### POST `/api/v1/audio/upload_multitrack`

**模式二**：上传多声道 WAV 文件（N 声道 = N 个发言人），后台异步处理。

**请求**：`multipart/form-data`
- `file`：WAV 文件（必需）
- `session_id`：会话 ID（query 参数，默认 `"default_session"`）

**响应：**
```json
{
  "status": "success",
  "message": "多声道文件已接收，正在后台处理",
  "session_id": "...",
  "mode": "multitrack",
  "file_info": {
    "filename": "meeting.wav",
    "channels": 3,
    "sample_rate": 16000,
    "duration_sec": 120.5
  }
}
```

### GET `/api/v1/audio/status`

查询服务状态和处理进度。

**响应：**
```json
{
  "is_capturing": false,
  "is_processing": true,
  "current_mode": "multitrack",
  "progress": 0.65,
  "result_count": 12,
  "track_info": { "channels": 3, "speakers": ["Speaker_1","Speaker_2","Speaker_3"] }
}
```

### GET `/api/v1/audio/tracks/{session_id}`

获取转录结果和完整会议文本。

**响应：**
```json
{
  "status": "success",
  "session_id": "...",
  "track_info": { ... },
  "results": [ {"speaker":"Speaker_1","text":"..."}, ... ],
  "full_text": "Speaker_1: ...\nSpeaker_2: ...",
  "is_complete": true
}
```

### GET `/api/v1/audio/devices`

列出系统可用音频设备（模式一选设备用）。

---

## 通用说明

- 所有服务均提供 `GET /health` 健康检查端点
- 所有 POST 请求的 Content-Type 为 `application/json`（upload_multitrack 除外）
- 错误响应统一格式：`{"status": "error", "message": "错误描述"}`
