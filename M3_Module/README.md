# Smart Meeting Assistant

这个仓库里有两个可独立使用的模块：

- `translation_module`：实时翻译
- `summary_module`：会议/对话摘要

根目录还有一个组合示例 `demo_meeting_pipeline.py`，会同时调用这两个模块。

如果想详细了解模块结构，优先看下面两份模块文档：

- [translation_module/README.md](translation_module/README.md)
- [summary_module/README.md](summary_module/README.md)

两个模块都依赖各自的 YAML 配置文件：

- [translation_module/config/translation.yml](translation_module/config/translation.yml)
- [summary_module/config/summary.yml](summary_module/config/summary.yml)

默认模式、模型名、后端类型、API 地址、密钥字段都在 YAML 里控制；文档里会分别说明每个关键项的作用和修改方式。

## Import 思路

这个项目已经在根目录放了 `__init__.py`，所以除了直接导入子模块外，也可以把整个项目当成一个包来用。

推荐的导入方式有三种：

### 1) 直接从根包导入

如果你的代码运行环境里，`M3_Module` 的上一级目录已经在 `PYTHONPATH` 中，或者你把项目安装成了可编辑包，就可以直接这样写：

```python
from M3_Module import create_summary_client, create_translation_client
```

这样会从根入口统一拿到两个模块的常用构造方法。

### 2) 直接从子模块导入

这是最常见、也最稳定的写法，适合在仓库内直接开发和调试：

```python
from summary_module import create_summary_client
from translation_module import create_translation_client
```

### 3) 在脚本里按项目结构调用

如果你直接运行根目录的示例脚本，比如 `demo_meeting_pipeline.py`，可以继续按照当前仓库结构引用这两个模块，不需要额外封装。

### 一个实用提醒

如果你发现 `import M3_Module` 找不到，通常不是代码问题，而是 Python 没有把项目根目录的上一级加入搜索路径。最简单的解决办法是：

- 在项目父目录下运行程序
- 或者把项目安装为可编辑包
- 或者继续使用 `summary_module` / `translation_module` 这两个子包导入

## 先看最小用法

### 1) 翻译模块

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
print(result.confidence)
print(result.latency_ms)
```

### 2) 摘要模块

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
print(result.confidence)
print(result.latency_ms)
```

## 翻译模块怎么用

### 创建客户端

```python
from translation_module import create_translation_client
```

参数：

- `src_lang`：源语言，默认 `en`
- `tgt_lang`：目标语言，默认 `zh`
- `config_path`：配置文件路径，默认 `config/translation.yml`
- `mode`：`api` 或 `local`，不传则读取配置文件里的 `mode`
- `tuning`：可选的 `TranslationTuningChannel`，用于前后处理

### 常用方法

- `translate_text(text, src_lang=None, tgt_lang=None) -> str`
- `translate_result(text, src_lang=None, tgt_lang=None) -> TranslationResult`
- `translate_many(texts, src_lang=None, tgt_lang=None) -> list[TranslationResult]`
- `translate_stream(source_chunks, src_lang=None, tgt_lang=None)`
- `sync_translate(...)`：同步兼容接口
- `process_stream(...)`：流式兼容接口

### 结果字段

`TranslationResult` 常用字段：

- `text`：翻译结果
- `confidence`：置信度
- `latency_ms`：耗时
- `is_final`：是否最终片段
- `src_offset`：源文本偏移

### 配置文件

文件：`translation_module/config/translation.yml`

- `mode`: `api` / `local`
- `api.api_key`: 现在默认写成 `${TRANSLATION_API_KEY}`，需要你在环境变量里提供
- `api.service`: `siliconflow | deepl | google | custom`
- `api.api_url`: API 地址
- `local.backend`: `stub | nllb | llm`
- `local.model_path`: 本地模型路径
- `local.multilingual` / `local.llm`: 只在对应后端生效

### 必要环境变量

如果你用 `api` 模式，先设置：

```bash
export TRANSLATION_API_KEY="你的翻译接口密钥"
```

### 命令行示例

```bash
python translation_module/standalone.py --mode local --text "Hello, how are you?" --src en --tgt zh
```

```bash
python translation_module/tests/demo_local_usage.py --backend stub --src en --tgt zh
```

## 摘要模块怎么用

### 创建客户端

```python
from summary_module import create_summary_client
```

参数：

- `config_path`：配置文件路径，默认 `config/summary.yml`
- `mode`：`api` 或 `local`，不传则读取配置文件里的 `mode`

### 常用方法

- `summarize_result(message) -> SummaryResult`
- `summarize_text(message) -> str`
- `reload()`：重新加载配置对应的实现
- `switch_mode(mode)`：切换 `api` / `local`

### 结果字段

`SummaryResult` 常用字段：

- `text`：摘要结果
- `confidence`：置信度
- `latency_ms`：耗时

### 配置文件

文件：`summary_module/config/summary.yml`

- `mode`: `api` / `local`
- `api.api_key`: 现在默认写成 `${SUMMARY_API_KEY}`
- `api.service`: 当前支持 `siliconflow` / `custom`
- `local.backend`: `mock | hf_seq2seq | hf_causal`
- `local.model_name_or_path`: 本地摘要模型名或路径
- `local.device`: `auto | cpu | cuda | mps`

### 必要环境变量

如果你用 `api` 模式，先设置：

```bash
export SUMMARY_API_KEY="你的摘要接口密钥"
```

### 命令行示例

```bash
python summary_module/standalone.py --mode local --text "Alice: 我们周五发版。\nBob: 我同意。"
```

```bash
python summary_module/tests/demo_local_usage.py --backend mock
```

## 组合示例

如果你想同时看“先摘要、再逐条翻译”的完整流程，直接运行根目录脚本：

```bash
python demo_meeting_pipeline.py
```

这个脚本会：

- 构造一段会议输入
- 调用 `SummaryClient` 生成摘要
- 调用 `TranslationClient` 逐条翻译会议内容
- 打印每一步结果

## 你最该记住的三件事

- 翻译入口：`create_translation_client(...)`
- 摘要入口：`create_summary_client(...)`
- API 模式别忘了设置 `TRANSLATION_API_KEY` 和 `SUMMARY_API_KEY`
