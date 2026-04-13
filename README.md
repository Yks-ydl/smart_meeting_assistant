# 智能会议助手 (Smart Meeting Assistant)

这是一个基于“重后端、轻前端”前后端分离架构的智能会议助手。后端完全基于 Python 生态开发，采用了微服务（Microservices）架构。

当前版本已将原 `Code/smart-meeting-frontend` 合并到本仓库 `frontend/` 目录，网关直接托管本地前端构建产物。

## 模块介绍

本项目按照设计规划了以下核心微服务：

- **M1 ASR Service** (`:8001`)：负责单轨语音处理，包括音频标准化、VAD、语言检测、ASR 与 BTS 风格后处理。
- **M2 Summary Service** (`:8002`)：负责智能会议纪要生成，采用 Reconstruct-before-Summarize 架构。
- **M3 Translation & Action** (`:8003`)：负责多语言翻译与待办事项抽取。
- **M4 Sentiment Service** (`:8004`)：负责会议情感与参与度分析。
- **M5 Gateway Service** (`:8000`)：后端总网关，提供 WebSocket 接口给前端与其他服务。
- **M6 Audio Input Service** (`:8005`)：负责读取本地目录中的多个独立音轨文件（默认支持 `.wav`、`.m4a`、`.mp3`、`.flac`、`.aac`、`.ogg`、`.webm`），逐轨调用 M1 并合并 transcript。
- **M7 Data Service** (`:8006`)：负责加载 VCSum 数据并提供字幕流/摘要查询接口。

## 当前语音标准

当前语音模块完全采用“**独立音轨**”方案：

- 每个参会人对应一个独立音频文件
- 输入目录中可以放多个分轨音频文件，默认支持 `.wav`、`.m4a`、`.mp3`、`.flac`、`.aac`、`.ogg`、`.webm`
- M6 读取目录并逐轨处理
- 每条音轨先做语言检测，再按检测语言转写
- speaker label 直接来自文件名或上游元数据
- 最终结果按时间戳合并输出

当前版本**不实现 speaker diarization**，也**不依赖 pyannote.audio 作为主流程**。

## 快速开始

1. **安装依赖**

   ```bash
   pip install -r requirements.txt
   ```

2. **配置环境变量（可选）**
   - `OPENAI_API_KEY`：如果要跑大模型模块
   - `M1_MODEL_SIZE_OR_PATH`：如果要指定本地 whisper 模型路径
   - `M1_DEVICE`：默认 `cpu`
   - `M1_COMPUTE_TYPE`：默认 `int8`
   - `MEETING_AUDIO_INPUT_DIR`：可选，覆盖 demo 模式默认读取的音频目录（默认仓库根目录 `audio/`）
   - `MEETING_DEMO_SOURCE`：可选，默认 `audio`；如需显式切回旧版 VCSum demo，可设为 `vcsum`
   - `VCSUM_SHORT_DATA_PATH`：可选，覆盖 M7 默认 short_train 数据路径
   - `VCSUM_LONG_DATA_PATH`：可选，覆盖 M7 默认 long_train 数据路径

3. **构建前端静态资源（网关托管）**

   ```bash
   cd frontend
   npm install
   npm run build
   ```

4. **一键启动微服务集群**

   ```bash
   python start_all.py
   ```

5. **直接从前端开始会议**

   默认 demo 流程会优先读取仓库根目录 `audio/` 下的分轨音频文件，并按现有字幕/翻译/会议纪要链路回放处理结果。

   如果你想改用其他目录，可以在启动前设置：

   ```env
   MEETING_AUDIO_INPUT_DIR=F:/path/to/meeting-audio
   ```

   如果你需要临时切回旧版 VCSum 数据集演示流，可设置：

   ```env
   MEETING_DEMO_SOURCE=vcsum
   ```

## M6 目录处理示例

将多个独立音轨放到本地目录，例如：

```text
/Users/orangezhi/Desktop/cityu/NLP/project/audio
├── audioOrangezhi11999480170.wav
└── audioYANGKaisen21999480170.wav
```

然后调用：

```bash
curl -X POST http://127.0.0.1:8005/api/v1/audio/process_directory \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "meeting_demo",
    "input_dir": "/Users/orangezhi/Desktop/cityu/NLP/project/audio",
      "glob_pattern": "*",
    "recursive": false
  }'
```

返回结果会包含：

- `track_info`
- `track_results`
- `merged_transcript`
- `full_text`

## Demo 默认流程

当前前端点击“开始会议”后，网关会执行以下顺序：

1. 读取 `input_dir` 请求参数；若未提供，则读取 `MEETING_AUDIO_INPUT_DIR`；若仍未提供，则默认使用仓库根目录 `audio/`
2. 调用 M6 `/api/v1/audio/process_directory`，默认自动发现目录中的受支持音频后缀
3. 复用现有 demo 的字幕流协议，把 `merged_transcript` 逐条回放为 `subtitle`
4. 继续沿用现有翻译、会议纪要、待办事项提取、情感与参与度分析链路

这意味着目录音频只是替换了 demo 流程最前面的“会议内容准备阶段”，后续 M2/M3/M4 的请求结构不变。

## 接口文档

各微服务启动后，均提供 OpenAPI (Swagger) 文档：

- M1 ASR 服务：http://127.0.0.1:8001/docs
- M2 摘要服务：http://127.0.0.1:8002/docs
- M3 翻译与待办服务：http://127.0.0.1:8003/docs
- M4 情感分析服务：http://127.0.0.1:8004/docs
- M5 主网关服务：http://127.0.0.1:8000/docs
- M6 音频输入服务：http://127.0.0.1:8005/docs
- M7 数据服务：http://127.0.0.1:8006/docs
