# AI 智能会议助手

基于微服务架构的智能会议分析系统，支持多人多轨音频录入、语音识别、实时翻译、情感分析与会议纪要自动生成。

## 系统架构

```
┌─────────────────────────────────────────────────────┐
│           M5 Gateway (Port 8000)                    │
│        WebSocket + REST 编排层                       │
└────┬───────┬───────┬───────┬───────┬────────────────┘
     │       │       │       │       │
     ▼       ▼       ▼       ▼       ▼
  M1 ASR  M2 摘要  M3 翻译  M4 情感  M6 音频输入
  :8001   :8002    :8003    :8004    :8005
```

| 模块 | 说明 |
|------|------|
| **M1 ASR** | 基于 Faster-Whisper 的语音识别，含 VAD、Speaker Attribution、文本后处理 |
| **M2 Summary** | 混合摘要架构：本地 BART 模型初步提取 + LLM API 精炼润色 |
| **M3 Translation** | LLM 驱动的多语言翻译与待办事项提取 |
| **M4 Sentiment** | LLM 驱动的情感分析与交互信号识别 |
| **M5 Gateway** | 主网关，WebSocket 实时编排 + REST 代理 + 全链路 Pipeline |
| **M6 Audio Input** | 本地目录多轨音频文件处理（m4a→wav 转换 + Speaker 标注 + 合并转录） |

## 项目结构

```
code/
├── m1_speech/                  # M1 语音处理核心模块
│   ├── asr/                    # ASR 转写器 + VAD
│   ├── io/                     # 音频加载 / 格式转换 / 导出
│   ├── pipeline/               # Speaker Attribution + Transcript Merger
│   ├── postprocess/            # 文本后处理（标点修正等）
│   ├── utils/                  # 配置数据类 + 通用 Schema
│   └── service.py              # SingleTrackSpeechService 统一服务层
├── M3_Module/                  # M3 模块化翻译 / 摘要子系统（可插拔后端）
│   ├── summary_module/         # 摘要模块（工厂模式，支持本地 / API）
│   └── translation_module/     # 翻译模块（工厂模式，支持多后端）
├── emotion_analyze/            # M4 离线情感分析模块
│   └── get_meeting_emotion.py  # MeetingSentimentAnalyzer（中英双语模型）
├── core/                       # 共享核心工具
│   ├── llm_utils.py            # LLM API 调用封装（兼容 OpenAI 格式）
│   └── text_utils.py           # 文本清洗 / 分段 / 合并 / 结构化解析
├── services/                   # 各微服务 FastAPI 入口
│   ├── asr_server.py           # M1 — Port 8001
│   ├── summary_server.py       # M2 — Port 8002
│   ├── translation_server.py   # M3 — Port 8003
│   ├── sentiment_server.py     # M4 — Port 8004
│   └── audio_input_server.py   # M6 — Port 8005
├── gateway/
│   └── main_server.py          # M5 网关 — Port 8000
├── tests/                      # 单元测试
├── experiments/                # 对比实验脚本
├── start_all.py                # 一键启动所有服务
├── requirements.txt            # Python 依赖
└── .env                        # 环境变量（API Key 等）
```

## 快速开始

### 1. 环境准备

```bash
# Python 3.10+
pip install -r requirements.txt
```

### 2. 配置环境变量

在 `code/` 目录下创建 `.env` 文件：

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
HF_ENDPOINT=https://hf-mirror.com
```

### 3. 启动服务

```bash
cd code
python start_all.py
```

启动后可访问各服务的 Swagger 文档：

- Gateway:    http://127.0.0.1:8000/docs
- M1 ASR:     http://127.0.0.1:8001/docs
- M2 Summary: http://127.0.0.1:8002/docs
- M3 Translate: http://127.0.0.1:8003/docs
- M4 Sentiment: http://127.0.0.1:8004/docs
- M6 Audio:   http://127.0.0.1:8005/docs

### 4. 使用方式

#### 方式一：全链路 Pipeline（推荐）

将多人录音文件（如 `.m4a`）放在同一目录下，文件名包含说话人标识（如 `audioAlice01.m4a`、`audioBob01.m4a`），然后调用：

```bash
curl -X POST http://127.0.0.1:8000/api/gateway/pipeline/full \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "meeting-001",
    "input_dir": "D:/recordings/meeting1",
    "glob_pattern": "*.m4a",
    "target_lang": "en"
  }'
```

该接口会自动完成：音频转换 → ASR 识别 → 摘要生成 + 翻译 + 待办提取。

#### 方式二：WebSocket 实时模式

通过 WebSocket 连接 `ws://127.0.0.1:8000/ws/meeting/{session_id}`，发送音频分片进行实时处理。

#### 方式三：直接调用各微服务 API

详见 [API_DOC.md](./API_DOC.md)。

## 技术栈

- **Web 框架**: FastAPI + Uvicorn
- **语音识别**: Faster-Whisper（CTranslate2 加速）
- **本地摘要模型**: BART / T5（Hugging Face Transformers）
- **LLM API**: 兼容 OpenAI 格式（DeepSeek / 通义千问等）
- **情感分析**: Chinese-Emotion（中文）+ RoBERTa go_emotions（英文）
- **音频处理**: torchaudio / librosa / soundfile
- **异步编排**: httpx + asyncio

## 环境变量说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | LLM API 密钥 | — |
| `OPENAI_BASE_URL` | LLM API 地址 | `https://api.deepseek.com` |
| `LLM_MODEL` | 模型名称 | `deepseek-chat` |
| `HF_ENDPOINT` | HuggingFace 镜像 | `https://hf-mirror.com` |
| `SUMMARY_MODEL` | 本地摘要模型 | `fnlp/bart-base-chinese` |
| `M1_MODEL_SIZE_OR_PATH` | Whisper 模型 | `small` |
| `M1_DEVICE` | 推理设备 | `cpu` |
| `M1_COMPUTE_TYPE` | 计算精度 | `int8` |
