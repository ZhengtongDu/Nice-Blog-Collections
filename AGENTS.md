# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## 仓库用途

收集优质英文博客原文，通过自动化 AI 管线翻译为微信公众号文章（Markdown 格式）。

## 目录约定

- `articles/{添加日期}-{slug}/` — 每篇文章一个文件夹
  - `metadata.yaml` — 元数据（标题、作者、原文日期、来源 URL、标签、状态）
  - `original.md` — 英文原文（Markdown）
  - `translated.md` — 中文翻译（微信公众号 Markdown）
- `src/` — 自动化翻译管线代码
  - `translate.py` — 管线入口脚本
  - `config.py` — Ollama / 翻译配置
  - `prompts/polish_prompt.md` — 模型润色规则

## 翻译管线

```bash
python src/translate.py <URL>
```

流程：爬取 → 清洗为 Markdown → Google Translate 按段翻译 → Ollama qwen3.5:9b 润色排版 → 输出 translated.md

## metadata.yaml status 字段

- `pending` — 待翻译
- `translated` — 已翻译
- `published` — 已发布到公众号

## 依赖

```bash
pip install -r requirements.txt
```

需要本地运行 Ollama 并拉取模型：`ollama pull qwen3.5:9b`
