# 博文翻译助手

收集优质英文博客，通过 AI 管线自动翻译为微信公众号文章的桌面应用。

## 功能特性

- **自动翻译管线**：输入 URL → 爬取 → Google Translate 翻译 → Ollama 润色 → 生成微信公众号格式文章
- **图片下载**：自动下载文章中的图片到本地
- **错误处理**：详细的错误日志和自动降级机制
- **SwiftUI 原生 macOS 工作台**：`Translate / Library / Review Queue / Settings`
- **审查发布**：渲染预览、Markdown 编辑、HTML 导出、公众号富文本复制
- **Python Worker 后端**：SwiftUI 只负责界面，翻译、存储、导出由后台 worker 统一处理

## 安装

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 安装 Ollama

```bash
# macOS
brew install ollama

# 启动服务
ollama serve

# 拉取模型
ollama pull qwen3.5:9b
```

## 使用方法

### 方式 1：运行新的 SwiftUI macOS app（推荐）

```bash
swift run BlogTranslatorApp
```

说明：
- 首次启动会选择内容库目录
- 当前使用 Swift Package 方式开发和运行
- 完整 `.app` 打包建议在安装完整 Xcode 后进行

### 方式 2：构建 `.app` bundle（开发打包）

```bash
./build_swiftui_app.sh
open "dist/博文翻译助手.app"
```

说明：
- 该脚本会把 Swift 可执行文件与 Python worker 源码一起打包进 `.app`
- 当前仍依赖本机可用的 Python 3 运行时和已安装的 Python 依赖

### 方式 3：命令行工具（保留）

```bash
python src/translate.py <URL>
```

### 方式 4：旧版 Tkinter GUI（兼容保留）

```bash
python src/gui/app.py
```

## SwiftUI 界面说明

### Translate

1. 输入文章 URL
2. 点击"开始翻译"
3. 查看 `Check Ollama / Fetch / Extract Metadata / Convert / Translate / Polish / Save` 阶段卡片
4. 实时查看任务日志
5. 翻译完成后文章会写入内容库并自动导出 `translated.html`

**错误处理**：
- 如果翻译失败，会显示错误提示
- 可以重新发起任务
- 失败日志会写入 `logs/errors/`
- 润色失败时会自动降级到 Google Translate 机翻结果

### Library / Review Queue

1. `Library` 显示全部文章，支持搜索和状态筛选
2. `Review Queue` 聚焦所有 `status=translated` 的文章
3. 中间内容区支持 `Preview / Markdown / Split`
4. 右侧 Inspector 支持状态更新、导出 HTML、复制公众号富文本、在 Finder 中打开

## 目录结构

```
博文翻译/
├── articles/                 # 文章存档
│   └── {date}-{slug}/
│       ├── metadata.yaml     # 元数据
│       ├── original.md       # 英文原文
│       ├── raw_translated.md # 机翻中间文件
│       ├── translated.md     # 最终翻译
│       └── images/           # 本地图片
├── log/                      # 项目复盘记录
│   └── YYYY-MM-DD.md
├── logs/                     # 运行时日志目录（不纳入版本控制）
│   ├── app.log               # 应用日志
│   └── errors/               # 错误日志
├── Package.swift             # Swift Package 入口
├── Sources/BlogTranslatorApp # SwiftUI macOS app
├── Tests/BlogTranslatorAppTests
├── src/
│   ├── core/                 # 核心业务逻辑
│   ├── gui/                  # GUI 界面
│   ├── utils/                # 工具函数
│   ├── worker/               # SwiftUI app 后台 worker
│   ├── translate.py          # 原命令行工具（仍可用）
│   └── config.py             # 配置文件
└── build_app.py              # 打包脚本
```

## 配置

编辑 `src/config.py` 可修改：

- Ollama 服务地址和模型
- 翻译超时时间
- Google Translate 重试次数
- 旧版 GUI 窗口大小

SwiftUI app 的内容库路径会写入本机用户设置，并在首次启动时选择。

## 故障排除

### Ollama 连接失败

```bash
# 检查 Ollama 是否运行
ollama list

# 重启服务
ollama serve
```

### 图片下载失败

图片下载失败不会中断翻译流程，会保留原始 URL。可以手动下载图片后放入 `articles/{slug}/images/` 目录。

### 润色失败

润色失败时会自动降级到 Google Translate 机翻结果，文章仍会保存。可以：
1. 查看错误日志了解原因
2. 手动编辑 `translated.md` 进行润色
3. 增加 `config.py` 中的 `POLISH_TIMEOUT` 配置

## 更新日志

### v1.0.0 (2026-03-23)

- ✅ 修复引用块问题（禁止使用 `>` 包裹正文）
- ✅ 添加图片下载功能
- ✅ 创建桌面 GUI 应用
- ✅ 完善错误处理和日志系统
- ✅ 支持审查发布工作流

## 许可证

MIT License
