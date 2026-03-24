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

if sys.version_info >= (3, 13):
    import html

    cgi_module = sys.modules.get("cgi")
    if cgi_module is None:
        cgi_module = type(sys)("cgi")
        sys.modules["cgi"] = cgi_module

    def _parse_header(line: str):
        parts = [part.strip() for part in line.split(";")]
        main_value = parts[0].lower() if parts else ""
        params = {}

        for part in parts[1:]:
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            params[key.lower().strip()] = value.strip().strip('"')

        return main_value, params

    cgi_module.escape = html.escape
    cgi_module.parse_header = _parse_header

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
    POLISH_TIMEOUT,
    USER_AGENT,
    GOOGLE_TRANSLATE_MAX_RETRIES,
    GOOGLE_TRANSLATE_RETRY_DELAY,
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
def ollama_translate_text(text: str) -> str:
    """使用 Ollama 本地模型翻译文本（Google Translate 的 fallback）"""
    prompt = f"请将以下英文翻译为中文，只输出翻译结果，不要解释：\n\n{text}"
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "think": False,
                "options": {"temperature": 0.3},
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        print(f"  [错误] Ollama 翻译也失败: {e}")
        return text


def google_translate_text(text: str, src: str = "en", dest: str = "zh-cn") -> str:
    """使用 Google Translate 翻译文本，失败时重试，最终 fallback 到 Ollama"""
    if not text.strip():
        return ""

    last_error = None

    for attempt in range(1, GOOGLE_TRANSLATE_MAX_RETRIES + 1):
        try:
            # 每次重试都创建新的 Translator 实例，避免复用坏连接
            translator = Translator()
            result = translator.translate(text, src=src, dest=dest)
            if attempt > 1:
                print(f"  [重试成功] 第 {attempt} 次尝试成功")
            return result.text
        except Exception as e:
            last_error = e
            if attempt < GOOGLE_TRANSLATE_MAX_RETRIES:
                delay = GOOGLE_TRANSLATE_RETRY_DELAY * (2 ** (attempt - 1))
                print(f"  [重试 {attempt}/{GOOGLE_TRANSLATE_MAX_RETRIES}] Google Translate 失败: {e}，{delay}s 后重试...")
                time.sleep(delay)
            else:
                print(f"  [失败] Google Translate 第 {attempt} 次尝试失败: {e}")

    print(f"  [回退] {GOOGLE_TRANSLATE_MAX_RETRIES} 次均失败，使用本地模型 ({OLLAMA_MODEL}) 翻译...")
    return ollama_translate_text(text)


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
    """调用 Ollama 进行润色排版，按章节分批处理避免超时"""
    meta_header = (
        f"- 原文标题：{metadata.get('title', '')}\n"
        f"- 作者：{metadata.get('author', '')}\n"
        f"- 原文链接：{metadata.get('source', '')}"
    )

    # 按 ## 拆分为章节分批润色
    original_sections = re.split(r"(?=^## )", original, flags=re.MULTILINE)
    translated_sections = re.split(r"(?=^## )", translated, flags=re.MULTILINE)

    # 确保数量对齐，不对齐时整篇一起发
    if len(original_sections) != len(translated_sections):
        original_sections = [original]
        translated_sections = [translated]

    polished_parts = []
    total = len(original_sections)

    for i, (orig_sec, trans_sec) in enumerate(zip(original_sections, translated_sections)):
        if not orig_sec.strip():
            continue

        is_first = (i == 0)
        is_last = (i == total - 1)

        section_instructions = []
        if is_first:
            section_instructions.append("这是文章的第一部分，请在开头添加著作权声明和摘要。")
        if is_last:
            section_instructions.append("这是文章的最后一部分，请在末尾添加译者总结。")
        if not is_first and not is_last:
            section_instructions.append("这是文章的中间部分，不需要添加著作权声明、摘要或译者总结。")

        extra = "\n".join(section_instructions)

        user_prompt = (
            f"请按照系统提示中的规则润色以下章节。\n\n"
            f"## 文章元数据\n{meta_header}\n\n"
            f"## 位置说明\n{extra}\n\n"
            f"## 英文原文\n{orig_sec.strip()}\n\n"
            f"## Google Translate 机翻结果\n{trans_sec.strip()}\n\n"
            f"请输出润色后的内容（Markdown 格式）："
        )

        print(f"  润色章节 {i + 1}/{total}...")
        try:
            resp = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": user_prompt,
                    "system": system_prompt,
                    "stream": False,
                    "think": False,
                    "options": {"temperature": 0.3, "num_predict": 4096},
                },
                timeout=POLISH_TIMEOUT,
            )
            resp.raise_for_status()
            part = resp.json().get("response", "")
            if part:
                polished_parts.append(part.strip())
            else:
                print(f"  [警告] 章节 {i + 1} 润色返回空，使用机翻原文")
                polished_parts.append(trans_sec.strip())
        except Exception as e:
            print(f"  [错误] 章节 {i + 1} 润色失败: {e}，使用机翻原文")
            polished_parts.append(trans_sec.strip())

    return "\n\n".join(polished_parts)
def slug_from_url(url: str) -> str:
    """从 URL 提取 slug"""
    path = url.rstrip("/").split("/")[-1]
    # 清理非法字符
    return re.sub(r"[^a-zA-Z0-9\-]", "", path) or "untitled"


def check_ollama() -> bool:
    """检查 Ollama 是否可用且模型已加载"""
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        if OLLAMA_MODEL not in models:
            print(f"[错误] Ollama 中未找到模型 {OLLAMA_MODEL}")
            print(f"  可用模型: {', '.join(models) or '无'}")
            print(f"  请运行: ollama pull {OLLAMA_MODEL}")
            return False
        # 测试实际生成
        test_resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": "hi",
                "stream": False,
                "think": False,
                "options": {"num_predict": 5},
            },
            timeout=60,
        )
        test_resp.raise_for_status()
        result = test_resp.json().get("response", "")
        if not result:
            print(f"[错误] {OLLAMA_MODEL} 生成测试返回空，模型可能异常")
            return False
        print(f"  Ollama 就绪 ({OLLAMA_MODEL})")
        return True
    except requests.ConnectionError:
        print(f"[错误] 无法连接 Ollama ({OLLAMA_BASE_URL})")
        print("  请确认 Ollama 已启动: ollama serve")
        return False
    except Exception as e:
        print(f"[错误] Ollama 检查失败: {e}")
        return False


def run_pipeline(url: str):
    """运行完整翻译管线"""
    print("[0/7] 检查 Ollama...")
    if not check_ollama():
        sys.exit(1)

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

    # 下载图片到本地
    print("  下载图片...")
    from core.image_downloader import download_images
    original_md = download_images(original_md, article_dir, url)

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

    # 拼接原文和翻译
    full_original = "\n\n".join(
        f"{s['original_heading']}\n\n{s['original_body']}"
        for s in translated_sections
    )
    full_translated = "\n\n".join(
        f"{s['heading']}\n\n{s['body']}" for s in translated_sections
    )

    # 保存机翻中间文件（用于对照检查，不纳入 git）
    raw_translated_path = article_dir / "raw_translated.md"
    raw_translated_path.write_text(full_translated, encoding="utf-8")
    print(f"  机翻中间文件: {raw_translated_path.name}")

    print("[6/7] Ollama 润色排版...")
    system_prompt = load_polish_prompt()

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
    print(f"  原文:     {original_path}")
    print(f"  机翻中间: {raw_translated_path} (不纳入 git)")
    print(f"  润色翻译: {translated_path}")


def main():
    if len(sys.argv) < 2:
        print("用法: python src/translate.py <URL>")
        print("示例: python src/translate.py https://example.com/blog-post")
        sys.exit(1)

    url = sys.argv[1]
    run_pipeline(url)


if __name__ == "__main__":
    main()
