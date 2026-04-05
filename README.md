# 智能会议助手 (Smart Meeting Assistant)

这是一个基于“重后端、轻前端”前后端分离架构的智能会议助手。后端完全基于 Python 生态开发，采用了微服务（Microservices）架构。

## 模块介绍

本项目按照设计规划了以下五个核心微服务：

- **M1 ASR Service** (`:8001`)：负责实时语音转文本（ASR）、说话人分离（Diarization）和后处理纠错（BTS）。
- **M2 Summary Service** (`:8002`)：负责智能会议纪要生成，采用 Reconstruct-before-Summarize 架构。
- **M3 Translation & Action** (`:8003`)：负责多语言实时机器翻译（MT）与上下文感知段落摘要事项提取。
- **M4 Sentiment Service** (`:8004`)：负责会议情感与参与度分析，捕捉同意、分歧等交互信号。
- **M5 Gateway Service** (`:8000`)：后端与工程化组长，提供 WebSocket 接口供前端推送音频数据并下发结果，使用 RESTful 调度上述微服务。

*注：目前各算法模块核心逻辑使用大模型 API（如 OpenAI / 阿里千问 / DeepSeek 等）进行 Mock 和原型验证。*

## 快速开始

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **配置环境变量**
   打开项目根目录的 `.env` 文件，填入您的 `OPENAI_API_KEY`。如果您使用国内大模型（例如 DeepSeek、千问），请取消注释并配置对应的 `OPENAI_BASE_URL`。
   > 若不配置 API Key，系统将返回内置的 Mock 文本，以便进行架构测试。

3. **一键启动微服务集群**
   ```bash
   python start_all.py
   ```

## 接口文档

各微服务启动后，均提供了 OpenAPI (Swagger) 可视化文档供独立测试：
- M1 ASR 服务：http://127.0.0.1:8001/docs
- M2 摘要服务：http://127.0.0.1:8002/docs
- M3 翻译与待办服务：http://127.0.0.1:8003/docs
- M4 情感分析服务：http://127.0.0.1:8004/docs
- M5 主网关服务：http://127.0.0.1:8000/docs
