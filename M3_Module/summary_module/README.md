# Summary Module

会议/对话摘要模块，核心思路是：把“输入一段多说话人的对话文本，输出结构化摘要”封装成一个稳定客户端，并通过工厂把 API 摘要和本地模型摘要解耦。

## 1. 设计目标

- 对外只暴露一个统一入口 `SummaryClient`
- 支持 `api` / `local` 两种实现模式
- 保持输入输出格式稳定，方便上层直接接入
- 用配置决定后端和模型，而不是把实现写死在业务代码里
- 适合会议纪要、行动项提取和冲突/共识总结场景

## 2. 架构总览

```text
Caller
  -> create_summary_client(...)
      -> SummaryClient
          -> SummarizerFactory
              -> APISummarizer / LocalSummarizer
                  -> SummaryResult
```

模块职责拆分为四层：

1. **入口层**：`summary_module/__init__.py` 导出 `SummaryClient` 和 `create_summary_client`
2. **编排层**：`core/client.py` 负责保存配置路径、模式和 summarizer 实例
3. **构造层**：`core/factory.py` 根据配置创建具体 summarizer
4. **实现层**：`impl/api/*` 和 `impl/local/*` 承载远程和本地摘要实现

## 3. 核心调用链

调用 `SummaryClient.summarize_result()` 时：

1. 客户端根据 `mode` 和 `config_path` 创建或复用 summarizer
2. summarizer 接收整段对话文本
3. API 或本地模型生成摘要
4. 返回统一的 `SummaryResult`

`summarize_text()` 只是对 `summarize_result()` 的一层轻封装，方便只拿文本结果的调用方。

## 4. 实现细节

### 4.1 客户端门面

`core/client.py` 里的 `SummaryClient` 是对外主入口。它负责：

- 保存配置路径 `config_path`
- 保存模式 `mode`
- 构造 summarizer
- 在配置变化后通过 `reload()` 重新加载实现
- 通过 `switch_mode()` 在 `api` 和 `local` 之间切换

这层的价值是把“如何选实现”与“如何使用摘要功能”分开。

### 4.2 工厂与缓存

`core/factory.py` 根据配置选择实现：

- 先加载 `config/summary.yml`
- 参数 `mode` 优先于配置文件中的 `mode`
- 模式只允许 `api` 或 `local`
- 缓存已经创建过的 summarizer，减少重复初始化

缓存对摘要模块尤其有用，因为远程客户端或本地模型在初始化时都可能比较重。

### 4.3 API 实现

`impl/api/api_summarizer.py` 负责远程摘要调用。它通过配置控制：

- `service`：服务类型
- `api_url`：服务端地址
- `api_key`：鉴权密钥
- `model`：请求模型
- `temperature`、`max_tokens`：生成参数
- `text_field`、`response_text_path`：请求与响应字段映射

当前配置中也保留了 `mock://` 这类开发态入口，方便在没有真实服务时验证调用链。

### 4.4 本地实现

`impl/local/local_summarizer.py` 负责本地推理场景。`local.backend` 目前支持：

- `mock`：开发占位，用于先打通链路
- `hf_seq2seq`：HuggingFace Seq2Seq 小模型
- `hf_causal`：HuggingFace causal 模型推理

其中 `mock` 的意义不是做规则摘要，而是提供一个可运行的本地链路，便于在模型未就绪时先验证系统集成。

### 4.5 统一结果结构

`core/interface.py` 定义了 `SummaryResult`：

- `text`：摘要文本
- `confidence`：结果置信度
- `latency_ms`：推理耗时

这个统一结构让 API 和本地实现可以互换，同时让上层报告或 UI 不必区分后端。

## 5. 配置说明

文件：`summary_module/config/summary.yml`

### 顶层配置

- `mode`：默认模式，`api` 或 `local`
- `api`：远程摘要参数
- `local`：本地推理参数

### API 模式关键项

- `api.service`：当前支持 `siliconflow` 和 `custom`
- `api.api_url`：API 地址
- `api.api_key`：默认使用 `${SUMMARY_API_KEY}`
- `api.model`：模型名
- `api.temperature`、`api.max_tokens`：生成参数

### Local 模式关键项

- `local.backend`：`mock | hf_seq2seq | hf_causal`
- `local.model_name_or_path`：本地模型名或路径
- `local.device`：`auto | cpu | cuda | mps`
- `local.max_new_tokens`：生成长度上限
- `local.temperature`：采样温度

### 必要环境变量

如果使用 API 模式，请先设置：

```bash
export SUMMARY_API_KEY="你的摘要接口密钥"
```

## 6. 使用示例

### 6.1 最小摘要调用

```python
from summary_module import create_summary_client

client = create_summary_client(
    config_path="summary_module/config/summary.yml",
    mode="local",
)

result = client.summarize_result(
    "Alice: 我们周五发版。\nBob: 我同意，先做回归测试。"
)
print(result.text)
```

### 6.2 切换模式

```python
client.switch_mode("api")
client.reload()
```

### 6.3 命令行运行

```bash
python summary_module/tests/demo_local_usage.py --backend mock
```

## 7. 报告可直接用的设计点

- 通过门面类隐藏底层实现差异，调用侧更简单
- 通过工厂按配置选择后端，便于切换 API 和本地模型
- 通过统一结果对象标准化输出，方便后续分析和展示
- 本地 `mock` 后端用于链路打通，真实模型后端用于能力验证
- 缓存机制减少重复初始化，适合长生命周期进程

## 8. 适合报告里写的能力点

摘要模块适合强调的能力包括：

- 对多人会议文本进行压缩总结
- 提炼决策、行动项、共识和冲突点
- 支持本地/远程两种部署方式
- 支持后续替换底层模型而不改上层调用

## 9. YAML 配置怎么改

配置文件是 [summary_module/config/summary.yml](summary_module/config/summary.yml)。它主要控制三类内容：默认模式、API 调用参数、本地摘要后端参数。

### 9.1 切换默认模式

```yaml
mode: "local"
```

`mode` 会影响 `create_summary_client(...)` 不传 `mode` 参数时走哪条链路。

### 9.2 配 API 模式

API 模式常改的键有：

```yaml
api:
    service: "siliconflow"
    api_url: "https://api.siliconflow.cn/v1/chat/completions"
    api_key: "${SUMMARY_API_KEY}"
    model: "Qwen/Qwen2.5-7B-Instruct"
    temperature: 0.2
    max_tokens: 512
```

如果你对接的是自定义服务，重点是确认 `api_key`、`api_url`、`text_field`、`response_text_path` 这几个字段和服务端约定一致。

### 9.3 配本地模式

本地摘要主要看 `local.backend`：

```yaml
local:
    backend: "hf_seq2seq"
    model_name_or_path: "fnlp/bart-base-chinese"
    device: "auto"
    max_new_tokens: 80
```

常见修改点：

- 想先验证流程：用 `mock`
- 想跑小模型：用 `hf_seq2seq`
- 想接你自己的本地推理模型：用 `hf_causal`

### 9.4 为什么 README 要专门说明 YAML

因为这个模块是“配置驱动”的：

- 报告里可以解释模式切换不是改代码，而是改 YAML
- 结果差异可以归因到后端、模型和生成参数
- 可复现性依赖于配置文件，而不是口头描述
