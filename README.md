# Nice Blog Collections

收集优质英文博客，通过 AI 管线自动翻译为微信公众号文章。

## 使用方法

```bash
pip install -r requirements.txt
python src/translate.py <文章URL>
```

需要本地运行 [Ollama](https://ollama.ai) 并拉取模型：

```bash
ollama pull qwen3.5:9b
```

## 目录结构

每篇文章存放在 `articles/{日期}-{slug}/` 下，包含原文、元数据和翻译。
