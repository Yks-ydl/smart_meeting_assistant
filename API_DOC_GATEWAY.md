# 前端与网关接口文档

本文档描述当前前端 `index.html` 与网关 `gateway/main_server.py` 之间的接口、参数和消息格式。

## 1. 当前架构

当前系统只保留一条主链路：

`前端 -> Gateway WebSocket /ws/pipeline/dir -> M6 -> M3/M4 -> M2/M3 -> 前端`

含义：
- 前端发起“目录批量流式回放”请求
- Gateway 先调用 M6 对整个目录做离线处理
- Gateway 再按每 5 秒一段的节奏，把转录结果流式推回前端
- 对每一段文本，Gateway 可选调用：
  - M3 翻译
  - M4 情感分析
- 每 30 秒可选提取一次增量待办
- 所有片段结束后，再生成：
  - 全局摘要
  - 全局待办

## 2. 前端调用的接口

### 2.1 WebSocket 主接口

- 地址：`ws://127.0.0.1:8000/ws/pipeline/dir`
- 用途：目录批量流式回放主入口
- 调用时机：前端点击“开始目录流式回放”按钮后建立连接

### 2.2 健康检查接口

- 地址：`GET /health`
- 用途：检查 Gateway 是否在线

- 地址：`GET /health/all`
- 用途：检查各微服务是否在线
- 前端顶部“刷新服务状态”按钮会调用该接口

## 3. 前端 -> 网关：消息类型

### 3.1 初始请求参数

前端在 WebSocket 建立成功后，会发送一条 JSON：

```json
{
  "session_id": "session-1712345678901",
  "input_dir": "D:/study/nlp/code/tests/audio",
  "glob_pattern": "*.wav",
  "target_lang": "en",
  "enable_translation": true,
  "enable_actions": true,
  "enable_sentiment": true
}
```

### 3.1 参数说明

| 参数名 | 类型 | 是否必填 | 默认值 | 说明 |
|---|---|---:|---|---|
| `session_id` | `string` | 否 | `session-${Date.now()}` | 本次任务的会话 ID，用于标识一次完整处理任务 |
| `input_dir` | `string` | 是 | 无 | 服务器本地音频目录的绝对路径，不是浏览器本地路径 |
| `glob_pattern` | `string` | 否 | `*.m4a` | 文件匹配模式，例如 `*.wav`、`*.m4a` |
| `target_lang` | `string` | 否 | `en` | 翻译目标语言，不填写时默认 English |
| `enable_translation` | `boolean` | 否 | `true` | 是否开启翻译模式，关闭后不调用 M3 翻译服务 |
| `enable_actions` | `boolean` | 否 | `true` | 是否开启待办提取，关闭后不调用 M3 待办提取服务 |
| `enable_sentiment` | `boolean` | 否 | `true` | 是否开启情感分析，关闭后不调用 M4 情感分析服务 |

## 4. 参数传递到网关后的行为

### 4.1 `session_id`
作用：
- 贯穿整个任务过程
- Gateway 调用 M6/M2/M3/M4 时会原样传递

### 4.2 `input_dir`
作用：
- 传给 M6
- 由 M6 扫描该目录下符合 `glob_pattern` 的音频文件

### 4.3 `glob_pattern`
作用：
- 传给 M6
- 决定处理哪些文件

示例：
- `*.wav`
- `*.m4a`
- `audio*.wav`

### 4.4 `target_lang`
作用：
- 不直接影响 M6
- 在 Gateway 对每个片段做翻译时，传给 M3

示例：
- `en`：翻译成英文
- `zh`：翻译成中文
- `ja`：翻译成日文

### 4.5 `enable_translation`
作用：
- `true`：Gateway 对每个片段调用 M3 翻译
- `false`：Gateway 不调用 M3 翻译，前端翻译模块也会隐藏

### 4.6 `enable_actions`
作用：
- `true`：
  - 每 30 秒调用一次 M3 提取增量待办
  - 结束时再调用一次 M3 提取全局待办
- `false`：
  - 不做增量待办
  - 不做最终全局待办
  - 前端待办模块隐藏

### 4.7 `enable_sentiment`
作用：
- `true`：Gateway 对每个片段调用 M4 做情感分析
- `false`：Gateway 不调用 M4，前端情感模块隐藏

## 5. 网关 -> 前端：WebSocket 消息类型

Gateway 会通过 WebSocket 持续向前端推送消息。每条消息都有 `type` 字段。

---

### 5.1 `info`

用途：
- 阶段提示信息
- 用于告诉前端当前进度

示例：

```json
{
  "type": "info",
  "message": "⏳ 阶段 1/3: 正在调用 M6 批量处理音频目录，这可能需要几分钟..."
}
```

字段说明：

| 字段名 | 类型 | 说明 |
|---|---|---|
| `type` | `string` | 固定为 `info` |
| `message` | `string` | 进度说明文本 |

---

### 5.2 `error`

用途：
- 任务失败时返回错误

示例：

```json
{
  "type": "error",
  "message": "未提取到任何转录文本"
}
```

字段说明：

| 字段名 | 类型 | 说明 |
|---|---|---|
| `type` | `string` | 固定为 `error` |
| `message` | `string` | 错误说明 |

---

### 5.3 `asr_result`

用途：
- 每 5 秒流式返回一段会议转录

示例：

```json
{
  "type": "asr_result",
  "data": {
    "speaker": "Alice",
    "text": "大家好，我们现在开始项目周会。",
    "start_time": 0.0,
    "end_time": 4.8
  }
}
```

字段说明：

| 字段名 | 类型 | 说明 |
|---|---|---|
| `type` | `string` | 固定为 `asr_result` |
| `data.speaker` | `string` | 说话人标签 |
| `data.text` | `string` | 本段识别文本 |
| `data.start_time` | `number` | 本段开始时间，单位秒 |
| `data.end_time` | `number` | 本段结束时间，单位秒 |

---

### 5.4 `analysis_result`

用途：
- 对当前这段转录返回附加分析
- 包含：
  - 翻译结果
  - 情感分析结果

示例：

```json
{
  "type": "analysis_result",
  "data": {
    "sentiment": {
      "status": "success",
      "label": "neutral"
    },
    "translation": {
      "status": "success",
      "translation": "Hello everyone, we are starting the weekly project meeting now."
    }
  }
}
```

字段说明：

| 字段名 | 类型 | 说明 |
|---|---|---|
| `type` | `string` | 固定为 `analysis_result` |
| `data.sentiment` | `object \| null` | 情感分析结果；关闭情感分析时可能为空 |
| `data.translation` | `object \| null` | 翻译结果；关闭翻译时可能为空 |

说明：
- `sentiment` 和 `translation` 的内部结构由下游服务决定
- 前端当前会优先尝试读取以下字段：
  - 翻译：`translation` / `text` / `data` / `result`
  - 情感：`sentiment` / `label` / `text` / `data` / `result`

---

### 5.5 `action_result`

用途：
- 每 30 秒返回一次增量待办事项

示例：

```json
{
  "type": "action_result",
  "data": {
    "actions": {
      "status": "success",
      "actions": [
        "Alice 负责整理需求文档",
        "Bob 下周前提交接口说明"
      ]
    },
    "window_start": 0.0,
    "window_end": 31.2
  }
}
```

字段说明：

| 字段名 | 类型 | 说明 |
|---|---|---|
| `type` | `string` | 固定为 `action_result` |
| `data.actions` | `object \| string \| array` | 增量待办结果 |
| `data.window_start` | `number` | 该批待办对应时间窗开始时间 |
| `data.window_end` | `number` | 该批待办对应时间窗结束时间 |

说明：
- 前端会把这批待办渲染成 `[00:00 - 00:30] xxx`
- 只有 `enable_actions=true` 时才会收到这种消息

---

### 5.6 `meeting_end_report`

用途：
- 所有片段回放完成后返回最终结果
- 包含：
  - 全局摘要
  - 全局待办

示例：

```json
{
  "type": "meeting_end_report",
  "data": {
    "summary": {
      "status": "success",
      "summary": "本次会议主要讨论了项目接口对齐、翻译模块输入格式以及后续分工。"
    },
    "actions": {
      "status": "success",
      "actions": [
        "Kaisen 输出统一总线接口文档",
        "各模块负责人和 Kaisen 对齐输入输出格式"
      ]
    }
  }
}
```

字段说明：

| 字段名 | 类型 | 说明 |
|---|---|---|
| `type` | `string` | 固定为 `meeting_end_report` |
| `data.summary` | `object` | 全局摘要结果 |
| `data.actions` | `object \| null` | 全局待办结果；若关闭待办提取则可能为空 |

说明：
- 前端会把 `summary` 显示在摘要卡片中
- `actions` 会以 `[全局] xxx` 的形式追加到待办区域中

## 6. 网关内部向各微服务传的参数

### 6.1 Gateway -> M6

地址：
- `http://127.0.0.1:8005/api/v1/audio/process_directory`

发送内容：

```json
{
  "session_id": "session-1712345678901",
  "input_dir": "D:/study/nlp/code/tests/audio",
  "glob_pattern": "*.wav",
  "recursive": false
}
```

字段说明：

| 字段名 | 类型 | 说明 |
|---|---|---|
| `session_id` | `string` | 会话 ID |
| `input_dir` | `string` | 音频目录 |
| `glob_pattern` | `string` | 文件匹配模式 |
| `recursive` | `boolean` | 是否递归扫描子目录，当前固定为 `false` |

---

### 6.2 Gateway -> M3 翻译

地址：
- `http://127.0.0.1:8003/api/v1/translation/translate`

发送内容：

```json
{
  "session_id": "session-1712345678901",
  "text": "大家好，我们现在开始项目周会。",
  "target_lang": "en"
}
```

字段说明：

| 字段名 | 类型 | 说明 |
|---|---|---|
| `session_id` | `string` | 会话 ID |
| `text` | `string` | 当前片段文本 |
| `target_lang` | `string` | 目标语言 |

只有 `enable_translation=true` 时才会调用。

---

### 6.3 Gateway -> M4 情感分析

地址：
- `http://127.0.0.1:8004/api/v1/sentiment/analyze`

发送内容：

```json
{
  "session_id": "session-1712345678901",
  "speaker": "Alice",
  "text": "大家好，我们现在开始项目周会。"
}
```

字段说明：

| 字段名 | 类型 | 说明 |
|---|---|---|
| `session_id` | `string` | 会话 ID |
| `speaker` | `string` | 当前片段说话人 |
| `text` | `string` | 当前片段文本 |

只有 `enable_sentiment=true` 时才会调用。

---

### 6.4 Gateway -> M3 待办提取（增量）

地址：
- `http://127.0.0.1:8003/api/v1/translation/extract_actions`

发送内容：

```json
{
  "session_id": "session-1712345678901",
  "text": "Alice: 大家好...\nBob: 我下周前提交接口文档..."
}
```

字段说明：

| 字段名 | 类型 | 说明 |
|---|---|---|
| `session_id` | `string` | 会话 ID |
| `text` | `string` | 某个 30 秒时间窗内累积的文本 |

只有 `enable_actions=true` 时才会调用。

---

### 6.5 Gateway -> M2 摘要

地址：
- `http://127.0.0.1:8002/api/v1/summary/generate`

发送内容：

```json
{
  "session_id": "session-1712345678901",
  "text": "完整会议全文..."
}
```

字段说明：

| 字段名 | 类型 | 说明 |
|---|---|---|
| `session_id` | `string` | 会话 ID |
| `text` | `string` | 完整会议全文 |

说明：
- 摘要目前没有开关，始终会调用

---

### 6.6 Gateway -> M3 待办提取（全局）

地址：
- `http://127.0.0.1:8003/api/v1/translation/extract_actions`

发送内容：

```json
{
  "session_id": "session-1712345678901",
  "text": "完整会议全文..."
}
```

字段说明与增量提取相同，只是这里传的是完整会议全文。

## 7. 前端字段来源说明

前端当前输入框与参数映射如下：

| 前端控件 ID | 发送字段 | 类型 | 说明 |
|---|---|---|---|
| `input_dir` | `input_dir` | `string` | 音频目录 |
| `glob_pattern` | `glob_pattern` | `string` | 文件匹配模式 |
| `target_lang` | `target_lang` | `string` | 翻译目标语言 |
| `session_id` | `session_id` | `string` | 会话 ID |
| `enable_translation` | `enable_translation` | `boolean` | 翻译开关 |
| `enable_actions` | `enable_actions` | `boolean` | 待办开关 |
| `enable_sentiment` | `enable_sentiment` | `boolean` | 情感开关 |

## 8. 默认值总结

| 参数 | 默认值 |
|---|---|
| `session_id` | `session-${Date.now()}` |
| `glob_pattern` | `*.m4a` |
| `target_lang` | `en` |
| `enable_translation` | `true` |
| `enable_actions` | `true` |
| `enable_sentiment` | `true` |

## 9. 一次完整交互示例

### 9.1 前端发送

```json
{
  "session_id": "session-1712345678901",
  "input_dir": "D:/study/nlp/code/tests/audio",
  "glob_pattern": "*.wav",
  "target_lang": "en",
  "enable_translation": true,
  "enable_actions": true,
  "enable_sentiment": true
}
```

### 9.2 网关可能依次返回

1. `info`
2. `asr_result`
3. `analysis_result`
4. `asr_result`
5. `analysis_result`
6. `action_result`
7. `asr_result`
8. `analysis_result`
9. `meeting_end_report`

## 10. 注意事项

- `input_dir` 必须是运行 Gateway/M6 的那台机器上的真实目录
- `target_lang` 空值会自动按 `en` 处理
- 如果关闭某个开关，网关不会调用对应微服务
- 当前摘要没有开关，始终生成
- WebSocket 是当前前端与网关之间最核心的业务接口

## 11. 当前唯一主业务接口总结

### 前端发送一次请求
- WebSocket: `/ws/pipeline/dir`

### 网关返回多条消息
- `info`
- `asr_result`
- `analysis_result`
- `action_result`
- `meeting_end_report`

---

## 12. 手动结束会议（前端 -> 网关）

前端在流式处理过程中可随时发送 `stop` 消息提前终止回放并触发摘要生成：

```json
{
  "type": "stop"
}
```

收到该消息后，网关将：
1. 停止继续推送剩余音频片段
2. 对已处理片段的文本生成全局摘要和待办（如已开启）
3. 推送 `meeting_end_report` 消息并关闭连接

这就是当前前端和网关之间完整的接口参数传递关系。