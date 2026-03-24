# 目录与文件约定

## 文章目录结构

每篇文章存放在 `articles/{YYYY-MM-DD}-{slug}/`，其中：
- 日期为文章添加日期（非原文发布日期）
- slug 取自 URL 路径最后一段（由 `slug_from_url()` 生成）

### 文件清单

| 文件 | 用途 | 版本控制 |
|------|------|----------|
| `metadata.yaml` | 元数据 | 是 |
| `original.md` | 英文原文（Markdown） | 是 |
| `raw_translated.md` | Google Translate 机翻中间文件 | 否（gitignore） |
| `translated.md` | 最终润色翻译 | 是 |
| `images/` | 本地下载的图片 | 是 |

### metadata.yaml 字段

```yaml
title: "文章标题（英文原标题）"
author: "作者名"
date: "YYYY-MM-DD"          # 原文发布日期
added: "YYYY-MM-DD"         # 添加到仓库的日期
source: "https://..."       # 原文 URL
tags: []                    # 标签列表
status: "pending"           # 状态
```

### status 生命周期

- `pending` — 待翻译
- `translated` — 已翻译，待审查
- `published` — 已发布到微信公众号

## 日志目录

- `log/` — 项目复盘记录，纳入版本控制，按日期命名（`YYYY-MM-DD.md`）
- `logs/` — 运行时日志（app.log、errors/），已 gitignore

## gitignore 要点

- `**/raw_translated.md` — 机翻中间文件不入库
- `logs/` — 运行时日志不入库
- `dist/`、`.build/` — 构建产物不入库
