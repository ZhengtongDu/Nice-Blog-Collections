# CLAUDE.md
<!-- 内容与 AGENTS.md 保持同步 -->

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

博文翻译助手 — 英文博客 AI 翻译管线 + 微信公众号发布工具。

## 快速参考

- 翻译文章：`conda run -n vx-blog python src/translate.py <URL>`
- SwiftUI app：`swift run BlogTranslatorApp`
- 构建并安装 .app：`./build_swiftui_app.sh`（自动安装到 /Applications）
- 测试：`swift test` / `conda run -n vx-blog python -m unittest discover -s tests -v`

## Python 环境

- 使用 conda 环境 `vx-blog`（`~/miniconda3/envs/vx-blog`）
- 安装依赖：`conda run -n vx-blog pip install -r requirements.txt`
- .app bundle 内嵌 `launch_worker.sh`，硬编码 conda python 路径

## 工作流约定

- 修改 Python 或 Swift 代码后，执行 `./build_swiftui_app.sh` 重新构建并安装 .app

## 知识文件索引

根据当前任务按需加载：

| 文件 | 何时加载 | 内容 |
|------|----------|------|
| `.claude/docs/conventions.md` | 处理文章、metadata、目录结构时 | 目录命名、metadata schema、文件约定 |
| `.claude/docs/architecture.md` | 修改 Python 或 Swift 代码时 | 系统架构、组件职责、管线流程、配置 |
| `.claude/docs/worker-protocol.md` | 修改 SwiftUI↔Python 通信时 | Worker JSON-lines IPC 协议参考 |
| `src/prompts/polish_prompt.md` | 调整润色效果时 | Ollama 润色排版规则（运行时加载） |
| `README.md` | 安装、使用、故障排除 | 用户文档 |

## 关键约定

- metadata status 生命周期：`pending` → `translated` → `published`
- 中文与英文/数字之间加空格
- `log/` = 项目复盘（版本控制），`logs/` = 运行时日志（gitignore）
