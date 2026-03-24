# 系统架构

## 概览

```
┌─────────────────────┐     JSON-lines      ┌──────────────────────┐
│  SwiftUI macOS App  │ ◄──── stdin/stdout ──►│  Python Worker       │
│  (Sources/Blog...)  │                       │  (src/worker/main.py)│
└─────────────────────┘                       └──────────┬───────────┘
                                                         │
                                              ┌──────────▼───────────┐
                                              │  翻译管线 Pipeline    │
                                              │  (src/core/)         │
                                              └──────────────────────┘

独立入口：
  - CLI: python src/translate.py <URL>
  - 旧版 GUI: python src/gui/app.py (Tkinter，兼容保留)
```

## Python 组件

| 目录 | 职责 |
|------|------|
| `src/core/pipeline.py` | TranslatePipeline 类，封装完整翻译流程 |
| `src/core/article_manager.py` | 文章 CRUD 操作 |
| `src/core/error_handler.py` | 错误日志记录（写入 `logs/errors/`） |
| `src/core/image_downloader.py` | 下载文章图片到本地 |
| `src/worker/main.py` | WorkerServer，JSON-lines IPC 服务端 |
| `src/worker/translation_job.py` | 翻译任务执行与进度上报 |
| `src/worker/content_store.py` | ArticleStore，文章存储读写 |
| `src/worker/markdown_renderer.py` | Markdown → HTML 渲染 |
| `src/gui/` | 旧版 Tkinter GUI（app.py、translate_tab.py、review_tab.py、widgets.py） |
| `src/utils/logger.py` | 日志工具 |
| `src/translate.py` | CLI 入口脚本 |
| `src/config.py` | 全局配置 |
| `src/prompts/polish_prompt.md` | Ollama 润色规则（运行时由 `load_polish_prompt()` 加载） |

## Swift 组件

`Sources/BlogTranslatorApp/` 下：
- `BlogTranslatorApp.swift` — App 入口
- `Models/AppModels.swift` — 数据模型
- `Views/` — SwiftUI 视图（Translate、Library、Review、Settings）
- `Components/` — 可复用 UI 组件
- `Utilities/` — 辅助工具

## 翻译管线阶段

```
check_ollama → fetch_html → extract_metadata → html_to_markdown
  → download_images → split_into_sections → translate_section (Google Translate)
  → ollama_polish → save (translated.md + metadata.yaml)
```

润色失败时自动降级到 Google Translate 机翻结果。

## 配置

`src/config.py` 关键参数：
- `OLLAMA_BASE_URL`: `http://localhost:11434`
- `OLLAMA_MODEL`: `qwen3.5:9b`
- `REQUEST_TIMEOUT`: 300s（单段翻译）
- `POLISH_TIMEOUT`: 600s（全文润色）
- `GOOGLE_TRANSLATE_MAX_RETRIES`: 3（指数退避，初始 2s）

## 构建与运行

详见 `README.md`。快速参考：
- 开发运行：`swift run BlogTranslatorApp`
- 构建 .app：`./build_swiftui_app.sh` → `dist/博文翻译助手.app`
- CLI：`python src/translate.py <URL>`
