# AI 智能会议助手 — API 接口文档

> 所有服务默认运行在 `127.0.0.1`，可通过 Gateway（端口 8000）统一访问，也可直接调用各微服务。

---

## 服务端口一览

| 服务 | 端口 | 说明 |
|------|------|------|
| M5 Gateway | 8000 | 主网关与编排 |
| M1 ASR | 8001 | 语音识别 |
| M2 Summary | 8002 | 会议摘要生成 |
| M3 Translation | 8003 | 翻译与待办提取 |
| M4 Sentiment | 8004 | 情感分析 |
| M6 Audio Input | 8005 | 音频输入处理 |

---

## 一、M1 — ASR 语音识别服务 (Port 8001)

### POST `/api/v1/asr/transcribe`

接收单轨音频（Base64 编码），返回转录结果。

**请求体：**
```json
{
  "audio_base64": "BASE64_ENCODED_AUDIO",
  "session_id": "meeting-001",
  "speaker_hint": "Alice",
  "source_channel": "audioAlice01",
  "chunk_start_time": 0.0,
  "language_hint": "zh",
  "audio_format": "wav"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| audio_base64 | string | 是 | Base64 编码的音频 |
| session_id | string | 是 | 会话 ID |
| speaker_hint | string | 否 | 说话人名称提示 |
| source_channel | string | 否 | 来源通道标识 |
| chunk_start_time | float | 否 | 片段起始时间（默认 0） |
| language_hint | string | 否 | 语言提示（zh/en） |
| audio_format | string | 否 | 音频格式（默认 webm） |

**响应示例：**
```json
{
  "status": "success",
  "session_id": "meeting-001",
  "speaker": "Alice",
  "text": "大家好今天讨论项目进度",
  "corrected_text": "大家好，今天讨论项目进度。",
  "language": "zh",
  "source_channel": "audioAlice01",
  "confidence": 0.92,
  "start_time": 0.0,
  "end_time": 5.2,
  "segments": [
    {
      "text": "大家好今天讨论项目进度",
      "start_time": 0.0,
      "end_time": 5.2,
      "speaker_label": "Alice",
      "confidence": 0.92,
      "source_channel": "audioAlice01",
      "language": "zh",
      "corrected_text": "大家好，今天讨论项目进度。"
    }
  ]
}
```

---

## 二、M2 — 会议摘要生成服务 (Port 8002)

### POST `/api/v1/summary/generate`

混合摘要生成（本地模型 + LLM 精炼），默认模式。

**请求体：**
```json
{
  "session_id": "meeting-001",
  "text": "完整的会议记录文本..."
}
```

**响应示例：**
```json
{
  "status": "success",
  "session_id": "meeting-001",
  "summary": "## 会议主旨\n...",
  "structured": {
    "main_topic": "讨论项目进度",
    "key_points": ["..."],
    "decisions": ["..."],
    "follow_ups": ["..."]
  },
  "mode": "hybrid"
}
```

### POST `/api/v1/summary/generate_local`

仅本地模型摘要（对比实验用），请求体同上。

### POST `/api/v1/summary/generate_llm`

仅 LLM API 摘要（对比实验用），请求体同上。

### POST `/api/v1/summary/evaluate`

ROUGE 评估（计算生成摘要与参考摘要之间的 ROUGE 分数）。

**请求体：**
```json
{
  "reference": "参考摘要文本",
  "hypothesis": "生成摘要文本"
}
```

**响应示例：**
```json
{
  "status": "success",
  "rouge_1": {"r": 0.85, "p": 0.78, "f": 0.81},
  "rouge_2": {"r": 0.60, "p": 0.55, "f": 0.57},
  "rouge_l": {"r": 0.80, "p": 0.75, "f": 0.77}
}
```

---

## 三、M3 — 翻译与待办提取服务 (Port 8003)

### POST `/api/v1/translation/translate`

多语言翻译。

**请求体：**
```json
{
  "session_id": "meeting-001",
  "text": "需要翻译的文本",
  "target_lang": "en"
}
```

**响应示例：**
```json
{
  "status": "success",
  "session_id": "meeting-001",
  "translated_text": "The text to translate"
}
```

### POST `/api/v1/translation/extract_actions`

提取会议待办事项。

**请求体：**
```json
{
  "session_id": "meeting-001",
  "text": "完整的会议记录文本..."
}
```

**响应示例：**
```json
{
  "status": "success",
  "session_id": "meeting-001",
  "action_items": "- [ ] 张三负责完成方案\n- [ ] 李四跟进客户反馈"
}
```

---

## 四、M4 — 情感分析服务 (Port 8004)

### POST `/api/v1/sentiment/analyze`

单句情感与交互信号分析。

**请求体：**
```json
{
  "session_id": "meeting-001",
  "speaker": "Alice",
  "text": "我觉得这个方案不太合适"
}
```

**响应示例：**
```json
{
  "status": "success",
  "session_id": "meeting-001",
  "speaker": "Alice",
  "analysis": {
    "sentiment": "negative",
    "signal": "disagreement",
    "explanation": "发言人表达了对方案的异议"
  }
}
```

---

## 五、M6 — 音频输入服务 (Port 8005)

### POST `/api/v1/audio/process_directory`

扫描本地目录中的音频文件，逐轨转换、送 M1 识别，合并为完整会议转录。

**请求体：**
```json
{
  "session_id": "meeting-001",
  "input_dir": "D:/recordings/meeting1",
  "glob_pattern": "*.m4a",
  "recursive": false
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | 是 | 会话 ID |
| input_dir | string | 是 | 音频文件所在目录路径 |
| glob_pattern | string | 否 | 文件匹配模式（默认 `*.m4a`） |
| recursive | bool | 否 | 是否递归搜索子目录（默认 false） |

**响应示例：**
```json
{
  "status": "success",
  "session_id": "meeting-001",
  "mode": "independent_tracks_from_directory",
  "input_dir": "D:/recordings/meeting1",
  "track_info": [
    {"filename": "audioAlice01.m4a", "source_channel": "audioAlice01", "speaker_label": "Alice", "detected_language": "zh"}
  ],
  "merged_transcript": [
    {"text": "...", "start_time": 0.0, "end_time": 5.2, "speaker_label": "Alice", "confidence": 0.92, "source_channel": "audioAlice01", "language": "zh", "corrected_text": "..."}
  ],
  "full_text": "[0000.00s - 0005.20s] Alice: 大家好...",
  "errors": []
}
```

### GET `/api/v1/audio/status`

查询当前处理任务状态。

### GET `/api/v1/audio/tracks/{session_id}`

获取指定会话的完整处理结果。

---

## 六、M5 — 网关编排端点 (Port 8000)

### WebSocket `/ws/meeting/{session_id}`

实时会议接口，支持以下消息类型：

**发送 — 音频分片：**
```json
{
  "type": "audio_chunk",
  "data": "BASE64_AUDIO",
  "speaker_hint": "Alice",
  "audio_format": "webm"
}
```

**发送 — 结束会议：**
```json
{
  "type": "end_meeting",
  "full_text": "完整会议记录..."
}
```

**接收消息类型：** `asr_result`、`asr_error`、`analysis_result`、`meeting_end_report`

### POST `/api/gateway/pipeline/full`

**全链路编排**：音频目录 → ASR → 摘要 + 翻译 + 待办 并行。

**请求体：**
```json
{
  "session_id": "meeting-001",
  "input_dir": "D:/recordings/meeting1",
  "glob_pattern": "*.m4a",
  "recursive": false,
  "target_lang": "en"
}
```

### REST 代理端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/gateway/audio/process_directory` | 代理 M6 目录处理 |
| GET  | `/api/gateway/audio/status` | 代理 M6 状态查询 |
| GET  | `/api/gateway/audio/tracks/{session_id}` | 代理 M6 结果查询 |
| POST | `/api/gateway/summary/generate` | 代理 M2 摘要 |
| POST | `/api/gateway/translation/translate` | 代理 M3 翻译 |
| POST | `/api/gateway/translation/extract_actions` | 代理 M3 待办提取 |
| POST | `/api/gateway/sentiment/analyze` | 代理 M4 情感分析 |

### GET `/health`

网关健康检查。

### GET `/health/all`

检查所有微服务健康状态。

---

## 通用说明

- 所有 POST 请求使用 `Content-Type: application/json`
- 所有响应包含 `status` 字段（`success` / `error`）
- 各服务的 Swagger 文档：`http://127.0.0.1:{port}/docs`
- 环境变量配置见 `.env` 文件（`OPENAI_API_KEY`、`OPENAI_BASE_URL` 等）
