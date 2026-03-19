"""
博文翻译管线

用法: python src/translate.py <URL>

流程: 爬取 → 清洗为 Markdown → Google Translate 按段翻译 → Ollama 润色排版 → 输出 translated.md
"""

import sys
import re
import json
import time
from pathlib import Path
from datetime import date

import requests
import yaml
from bs4 import BeautifulSoup
import html2text
from googletrans import Translator

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent))
from config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    MAX_CHARS_PER_CHUNK,
    REQUEST_TIMEOUT,
    USER_AGENT,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTICLES_DIR = PROJECT_ROOT / "articles"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def fetch_html(url: str) -> str:
    """爬取网页 HTML"""
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    return resp.text


def extract_metadata(soup: BeautifulSoup, url: str) -> dict:
    """从 HTML meta 标签提取文章元数据"""
    meta = {"source": url, "added": str(date.today()), "status": "pending"}

    # 标题
    og_title = soup.find("meta", property="og:title")
    if og_title:
        title = og_title.get("content", "")
        # 去掉网站名后缀
        meta["title"] = re.sub(r"\s*\|.*$", "", title).strip()
    elif soup.title:
        meta["title"] = soup.title.string.strip()
    else:
        meta["title"] = "Untitled"

    # 作者
    author_meta = soup.find("meta", attrs={"name": "author"})
    if author_meta:
        meta["author"] = author_meta.get("content", "Unknown")
    else:
        meta["author"] = "Unknown"

    # 发布日期
    date_meta = soup.find("meta", property="article:published_time")
    if date_meta:
        raw = date_meta.get("content", "")
        meta["date"] = raw[:10]  # 取 YYYY-MM-DD
    else:
        meta["date"] = str(date.today())

    # 标签
    meta["tags"] = []

    return meta


def html_to_markdown(html_content: str) -> str:
    """将 HTML 转换为干净的 Markdown"""
    soup = BeautifulSoup(html_content, "html.parser")

    # 尝试找到文章正文区域
    article = (
        soup.find("article")
        or soup.find("div", class_="prose")
        or soup.find("div", id="article-content")
        or soup.find("main")
    )
    if article is None:
        article = soup.body or soup

    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = True
    converter.ignore_emphasis = False
    converter.body_width = 0  # 不自动换行
    converter.unicode_snob = True

    md = converter.handle(str(article))

    # 清理多余空行
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


def split_into_sections(markdown: str) -> list[dict]:
    """按 ## 标题拆分为章节"""
    sections = []
    current_heading = ""
    current_body = []

    for line in markdown.split("\n"):
        if line.startswith("## "):
            if current_heading or current_body:
                sections.append({
                    "heading": current_heading,
                    "body": "\n".join(current_body).strip(),
                })
            current_heading = line
            current_body = []
        else:
            current_body.append(line)

    # 最后一个章节
    if current_heading or current_body:
        sections.append({
            "heading": current_heading,
            "body": "\n".join(current_body).strip(),
        })

    return sections
def google_translate_text(text: str, src: str = "en", dest: str = "zh-cn") -> str:
    """使用 Google Translate 翻译文本"""
    if not text.strip():
        return ""
    translator = Translator()
    try:
        result = translator.translate(text, src=src, dest=dest)
        return result.text
    except Exception as e:
        print(f"  [警告] Google Translate 失败，返回原文: {e}")
        return text


def translate_section(section: dict) -> dict:
    """翻译单个章节（标题 + 正文）"""
    translated_heading = ""
    if section["heading"]:
        heading_text = section["heading"].lstrip("# ").strip()
        translated_heading = google_translate_text(heading_text)
        translated_heading = f"## {translated_heading}"

    # 按段落翻译正文，避免超长文本
    paragraphs = section["body"].split("\n\n")
    translated_paragraphs = []
    for para in paragraphs:
        if not para.strip():
            continue
        # 对于过长段落，分块翻译
        if len(para) > MAX_CHARS_PER_CHUNK:
            chunks = [
                para[i : i + MAX_CHARS_PER_CHUNK]
                for i in range(0, len(para), MAX_CHARS_PER_CHUNK)
            ]
            translated = "".join(google_translate_text(c) for c in chunks)
        else:
            translated = google_translate_text(para)
        translated_paragraphs.append(translated)

    return {
        "heading": translated_heading,
        "body": "\n\n".join(translated_paragraphs),
        "original_heading": section["heading"],
        "original_body": section["body"],
    }


def load_polish_prompt() -> str:
    """加载润色 prompt"""
    prompt_path = PROMPTS_DIR / "polish_prompt.md"
    return prompt_path.read_text(encoding="utf-8")


def ollama_polish(
    system_prompt: str,
    original: str,
    translated: str,
    metadata: dict,
) -> str:
    """调用 Ollama 进行润色排版"""
    user_prompt = f"""以下是一篇英文博客文章的原文和 Google Translate 机翻结果。请按照系统提示中的规则进行润色和排版。

## 文章元数据
- 原文标题：{metadata.get('title', '')}
- 作者：{metadata.get('author', '')}
- 原文链接：{metadata.get('source', '')}

## 英文原文
{original}

## Google Translate 机翻结果
{translated}

请输出润色后的完整中文文章（Markdown 格式）："""

    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": user_prompt,
                "system": system_prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 8192},
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")
    except Exception as e:
        print(f"  [错误] Ollama 调用失败: {e}")
        return ""
def slug_from_url(url: str) -> str:
    """从 URL 提取 slug"""
    path = url.rstrip("/").split("/")[-1]
    # 清理非法字符
    return re.sub(r"[^a-zA-Z0-9\-]", "", path) or "untitled"


def run_pipeline(url: str):
    """运行完整翻译管线"""
    print(f"[1/7] 爬取文章: {url}")
    html_content = fetch_html(url)
    soup = BeautifulSoup(html_content, "html.parser")

    print("[2/7] 提取元数据...")
    metadata = extract_metadata(soup, url)
    slug = slug_from_url(url)
    article_dir = ARTICLES_DIR / f"{date.today().isoformat()}-{slug}"
    article_dir.mkdir(parents=True, exist_ok=True)

    print(f"  标题: {metadata['title']}")
    print(f"  作者: {metadata['author']}")
    print(f"  目录: {article_dir.name}")

    print("[3/7] 转换为 Markdown...")
    original_md = html_to_markdown(html_content)
    original_path = article_dir / "original.md"
    original_path.write_text(
        f"# {metadata['title']}\n\n{original_md}", encoding="utf-8"
    )

    # 保存 metadata
    meta_path = article_dir / "metadata.yaml"
    with open(meta_path, "w", encoding="utf-8") as f:
        yaml.dump(metadata, f, allow_unicode=True, default_flow_style=False)

    print("[4/7] 拆分章节...")
    sections = split_into_sections(original_md)
    print(f"  共 {len(sections)} 个章节")

    print("[5/7] Google Translate 翻译...")
    translated_sections = []
    for i, section in enumerate(sections):
        heading_preview = (
            section["heading"][:40] if section["heading"] else "(开头)"
        )
        print(f"  翻译章节 {i + 1}/{len(sections)}: {heading_preview}")
        translated_sections.append(translate_section(section))
        time.sleep(0.5)  # 避免请求过快

    print("[6/7] Ollama 润色排版...")
    system_prompt = load_polish_prompt()

    # 拼接原文和翻译
    full_original = "\n\n".join(
        f"{s['original_heading']}\n\n{s['original_body']}"
        for s in translated_sections
    )
    full_translated = "\n\n".join(
        f"{s['heading']}\n\n{s['body']}" for s in translated_sections
    )

    polished = ollama_polish(system_prompt, full_original, full_translated, metadata)

    if not polished:
        print("  [警告] Ollama 润色失败，使用 Google Translate 原始结果")
        polished = full_translated

    print("[7/7] 保存结果...")
    translated_path = article_dir / "translated.md"
    translated_path.write_text(polished, encoding="utf-8")

    # 更新状态
    metadata["status"] = "translated"
    with open(meta_path, "w", encoding="utf-8") as f:
        yaml.dump(metadata, f, allow_unicode=True, default_flow_style=False)

    print(f"\n完成! 文件保存在: {article_dir}")
    print(f"  原文: {original_path}")
    print(f"  翻译: {translated_path}")


def main():
    if len(sys.argv) < 2:
        print("用法: python src/translate.py <URL>")
        print("示例: python src/translate.py https://example.com/blog-post")
        sys.exit(1)

    url = sys.argv[1]
    run_pipeline(url)


if __name__ == "__main__":
    main()
