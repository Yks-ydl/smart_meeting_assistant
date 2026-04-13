# Translation Module

实时翻译模块，采用“客户端门面 + 工厂 + 多实现后端”的结构。模块的目标不是把翻译逻辑写死，而是通过统一接口把 API 翻译、本地推理、流式处理和调优通道串成一条可切换的链路。

## 1. 设计目标

- 对外只暴露一个稳定入口 `TranslationClient`
- 支持 `api` / `local` 两种模式切换
- 保持同步翻译、批量翻译、流式翻译三类调用统一
- 通过配置文件驱动服务端点、模型、语言对和本地后端
- 允许在不改调用方代码的情况下替换翻译实现

## 2. 架构总览

```text
Caller
  -> create_translation_client(...)
      -> TranslationClient
          -> TranslatorFactory
              -> APITranslator / LocalInferenceTranslator / LLMTranslator
                  -> TranslationResult
```

更细一点看，模块的职责可以拆成四层：

1. **入口层**：`translation_module/__init__.py` 导出 `TranslationClient` 和 `create_translation_client`
2. **编排层**：`core/client.py` 负责保存语言对、调优通道和 translator 实例
3. **构造层**：`core/factory.py` 根据配置创建具体实现，并处理缓存
4. **实现层**：`impl/api/*` 和 `impl/local/*` 分别承载 API 与本地推理逻辑

## 3. 核心调用链

### 3.1 同步翻译

调用 `TranslationClient.sync_translate()` 时：

1. 客户端解析 `src_lang` / `tgt_lang`
2. 把文本交给当前 translator
3. 传入 `pre_hook` 和 `post_hook`
4. translator 返回 `TranslationResult`
5. 上层按需读取 `text`、`confidence` 和 `latency_ms`

### 3.2 流式翻译

调用 `TranslationClient.process_stream()` 或 `translate_stream()` 时：

1. 上游提供 `AsyncIterator[str]`
2. 客户端把输入流交给 translator
3. translator 结合分块、缓冲、后处理逻辑逐步产出结果
4. 每个结果都用同一个 `TranslationResult` 结构表示

### 3.3 调优通道

`TranslationTuningChannel` 是模块的一条可插拔“前后处理链”：

- `apply_pre()`：翻译前的文本规整、领域词替换或提示词整理
- `apply_post()`：翻译后的文本修整、术语回填或格式统一

这样做的好处是，调用方不用关心模型细节，也不用在业务代码里重复写清洗逻辑。

## 4. 实现细节

### 4.1 客户端门面

`core/client.py` 里的 `TranslationClient` 是唯一建议直接使用的类。它做三件事：

- 保存默认语言对 `src_lang` / `tgt_lang`
- 保存 `config_path`、`mode` 和 `tuning`
- 负责懒重建 translator、模式切换和批量兼容接口

常见方法：

- `translate_result()`：返回完整结果对象
- `translate_text()`：只返回翻译后的字符串
- `translate_many()`：批量同步翻译
- `translate_stream()`：异步流式翻译
- `sync_translate()`、`process_stream()`：为了兼容骨架系统的命名习惯

### 4.2 工厂与缓存

`core/factory.py` 是模块的真正“实现选择器”。它会：

- 先读取 `config/translation.yml`
- 再决定最终模式：参数 `mode` 优先于配置文件 `mode`
- 校验模式只能是 `api` 或 `local`
- 对 API translator 做实例缓存
- 对本地 LLM 模型做模型级缓存，避免重复加载

这里的缓存设计很重要：

- **API 模式**：同一配置下通常可以复用一个 translator 实例
- **LLM 本地模式**：模型加载最重，因此单独缓存 `LLMModel`
- **local 非 LLM 模式**：按 `backend` 区分缓存 key，避免不同后端相互污染

### 4.3 API 实现

`impl/api/api_translator.py` 负责调用远程翻译服务。配置通过 `api` 节点控制，支持：

- `service`：`siliconflow | deepl | google | custom`
- `api_url`：接口地址
- `api_key`：鉴权密钥
- `text_field` / `src_lang_field` / `tgt_lang_field`：请求字段映射
- `response_text_path` / `response_confidence_path`：响应解析路径

这意味着同一个 API 适配层可以对接多个供应商，而不必让上层改代码。

### 4.4 本地实现

本地翻译模式由 `impl/local/*` 承载，分成两条路线：

- `LocalInferenceTranslator`：面向传统本地模型或轻量后端
- `LLMTranslator`：面向本地大模型 / 微调模型 / LoRA 场景

配置里的 `local.backend` 决定最终走哪条路线：

- `stub`：开发占位，用于先打通流程
- `nllb`：多语言模型后端
- `llm`：本地 LLM 推理后端

### 4.5 统一结果结构

`core/interface.py` 定义了 `TranslationResult`，它把各种后端的输出统一成同一种数据结构。这样做的价值是：

- API 和本地实现可以完全不同，但调用方看到的字段一致
- 流式与非流式结果能共享同一对象
- 上游业务可以直接消费 `text` / `confidence` / `latency_ms`

## 5. 配置说明

文件：`translation_module/config/translation.yml`

### 顶层配置

- `mode`：默认模式，`api` 或 `local`
- `api`：远程调用参数
- `local`：本地推理参数
- `pipeline`：缓冲、切分等流式处理参数

### API 模式关键项

- `api.service`：选择服务商
- `api.api_url`：服务端地址
- `api.api_key`：默认使用 `${TRANSLATION_API_KEY}`
- `api.model`：请求模型名
- `api.temperature`、`api.max_tokens`：生成参数

### Local 模式关键项

- `local.backend`：`stub | nllb | llm`
- `local.model_path`：本地模型路径
- `local.quantized`：是否使用量化模型
- `local.multilingual`：`nllb` 等多语言后端配置
- `local.llm`：`llm` 后端配置，包括模型 ID、量化方式和 prompt 模板

### 必要环境变量

如果使用 API 模式，请先设置：

```bash
export TRANSLATION_API_KEY="你的翻译接口密钥"
```

## 6. 使用示例

### 6.1 最小同步翻译

```python
from translation_module import create_translation_client

client = create_translation_client(
    src_lang="en",
    tgt_lang="zh",
    config_path="translation_module/config/translation.yml",
    mode="local",
)

result = client.sync_translate("Hello, how are you?")
print(result.text)
```

### 6.2 批量翻译

```python
results = client.translate_many(["Hello", "How are you?"])
for item in results:
    print(item.text)
```

### 6.3 流式翻译

```python
async for result in client.process_stream(source_chunks):
    print(result.text, result.is_final)
```

## 7. 报告可直接用的设计点

- 采用“门面 + 工厂 + 多实现”模式降低外部耦合
- 用配置文件切换 API / 本地实现，增强可部署性
- 用统一结果对象屏蔽后端差异，提升接口稳定性
- 用缓存减少 API translator 和本地模型的重复初始化成本
- 用调优通道把前后处理从翻译核心逻辑中剥离出去

## 8. 常用运行方式

```bash
python translation_module/tests/demo_local_usage.py --backend stub --src en --tgt zh
```

## 9. YAML 配置怎么改

配置文件是 [translation_module/config/translation.yml](translation_module/config/translation.yml)。这个文件决定了三件事：

- 默认走 `api` 还是 `local`
- 远程 API 的地址、密钥和请求字段
- 本地模型后端、模型路径和生成参数

常见修改方式如下：

### 9.1 切换默认模式

把最上面的 `mode` 改成你想要的值：

```yaml
mode: "local"
```

如果写成 `api`，客户端默认就会走远程接口；如果写成 `local`，客户端默认就会走本地推理。

### 9.2 配 API 模式

API 模式最关键的是这几个键：

```yaml
api:
    service: "siliconflow"
    api_url: "https://api.siliconflow.cn/v1/chat/completions"
    api_key: "${TRANSLATION_API_KEY}"
```

如果你接的是自定义服务，通常还要一起改请求字段和响应字段：

```yaml
api:
    service: "custom"
    text_field: "text"
    src_lang_field: "src_lang"
    tgt_lang_field: "tgt_lang"
    response_text_path: "data.text"
    response_confidence_path: "data.confidence"
```

### 9.3 配本地模式

本地模式由 `local.backend` 决定后端：

```yaml
local:
    backend: "llm"
```

不同 backend 的关注点不同：

- `stub`：最轻量，只用于打通链路
- `nllb`：改 `model_path`、`device`、`multilingual`
- `llm`：改 `local.llm` 下的 `model_id`、`quantization`、`prompt_template`

### 9.4 流式处理参数

如果你要更细地调流式翻译，可看 `pipeline` 节点里的缓冲和切分参数，例如：

```yaml
pipeline:
    buffer_size: 3
    max_delay_ms: 300
```

这些参数会影响流式输入合并、输出节奏和片段延迟。
