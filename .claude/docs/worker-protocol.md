# Worker JSON-lines 协议参考

SwiftUI app 通过 subprocess 启动 `python3 -m src.worker.main`，经 stdin/stdout 以 JSON-lines 格式通信。

源码：`src/worker/main.py`

## 消息格式

### 请求（SwiftUI → Python）

```json
{"id": "uuid", "command": "命令名", "params": {}}
```

### 响应（Python → SwiftUI）

```json
{"type": "response", "id": "uuid", "ok": true, "result": {}}
{"type": "response", "id": "uuid", "ok": false, "error": {"message": "..."}}
```

### 事件（Python → SwiftUI，主动推送）

```json
{"type": "event", "event": "事件名", "payload": {}}
```

## 命令参考

| 命令 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `health_check` | 无 | worker/Ollama/model 状态 | 含 `workerReady`、`ollamaReachable`、`modelInstalled` |
| `set_storage_root` | `{path}` | 同 health_check | 更新文章存储根目录，触发 `articles_changed` 事件 |
| `start_translation` | `{url}` | job snapshot | URL 须以 `http` 开头；同时只能有一个活跃任务 |
| `cancel_job` | `{jobId}` | `{jobId, accepted}` | 取消指定翻译任务 |
| `list_articles` | `{status?, search?, sort?}` | 文章列表 | sort 默认 `added_desc` |
| `get_article` | `{articleId}` | 文章完整内容 | articleId 为文章目录名 |
| `save_translated_markdown` | `{articleId, markdown}` | 保存结果 | 触发 `article_saved` + `articles_changed` |
| `update_status` | `{articleId, status}` | 更新结果 | 触发 `articles_changed` |
| `export_article_html` | `{articleId}` | `{path}` | 导出 HTML，触发 `html_exported` |

## 事件类型

| 事件 | 触发时机 |
|------|----------|
| `articles_changed` | 存储根变更、文章保存、状态更新 |
| `article_saved` | translated.md 保存成功 |
| `html_exported` | HTML 导出完成 |
| `job_progress` | 翻译任务进度更新（由 TranslationJob 发出） |
| `job_finished` | 翻译任务完成或失败（由 TranslationJob 发出） |

## 并发模型

- 同一时刻只允许一个活跃翻译任务（`_active_job`）
- stdout 写入通过 `_write_lock`（threading.Lock）序列化，防止 JSON-lines 交错
- 翻译任务在独立线程中执行，通过 `_send_event` 回调推送进度

## 错误处理

- JSON 解析失败：返回 `id: null` 的错误响应
- 命令执行异常：捕获 Exception，返回 `ok: false` + 错误消息
- 未知命令：抛出 `ValueError("未知命令: ...")`
