"""Lightweight Markdown to HTML rendering for preview/export.

This renderer intentionally supports a small subset of Markdown well enough
for the generated微信公众号文章 workflow in this repository.
"""

from __future__ import annotations

from html import escape
import re


_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_CODE_RE = re.compile(r"`([^`]+)`")


def _stash_tokens(text: str):
    tokens: dict[str, str] = {}

    def stash(pattern: re.Pattern[str], formatter):
        nonlocal text

        def replace(match: re.Match[str]) -> str:
            key = f"ZZZTOKENPLACEHOLDER{len(tokens)}ZZZ"
            tokens[key] = formatter(match)
            return key

        text = pattern.sub(replace, text)

    stash(
        _CODE_RE,
        lambda m: f"<code>{escape(m.group(1), quote=False)}</code>",
    )
    stash(
        _IMAGE_RE,
        lambda m: (
            f'<img alt="{escape(m.group(1))}" '
            f'src="{escape(m.group(2))}" loading="lazy" />'
        ),
    )
    stash(
        _LINK_RE,
        lambda m: (
            f'<a href="{escape(m.group(2))}">{escape(m.group(1), quote=False)}</a>'
        ),
    )

    return text, tokens


def render_inline(text: str) -> str:
    """Render inline Markdown spans."""
    text, tokens = _stash_tokens(text)
    text = escape(text, quote=False)

    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"<em>\1</em>", text)
    text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", text)

    for key, value in tokens.items():
        text = text.replace(key, value)

    return text


def _is_unordered_item(line: str) -> bool:
    return bool(re.match(r"^\s*[-*]\s+", line))


def _is_ordered_item(line: str) -> bool:
    return bool(re.match(r"^\s*\d+\.\s+", line))


def _strip_list_marker(line: str) -> str:
    return re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", line).strip()


def _render_blocks(lines: list[str]) -> str:
    parts: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped.startswith("```"):
            language = stripped[3:].strip()
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            class_attr = f' class="language-{escape(language)}"' if language else ""
            code = escape("\n".join(code_lines), quote=False)
            parts.append(f"<pre><code{class_attr}>{code}</code></pre>")
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            level = len(heading.group(1))
            parts.append(f"<h{level}>{render_inline(heading.group(2).strip())}</h{level}>")
            i += 1
            continue

        if re.match(r"^([-*_])\1{2,}$", stripped):
            parts.append("<hr />")
            i += 1
            continue

        if stripped.startswith(">"):
            quote_lines: list[str] = []
            while i < len(lines):
                current = lines[i]
                current_stripped = current.strip()
                if current_stripped.startswith(">"):
                    quote_lines.append(re.sub(r"^\s*>\s?", "", current))
                    i += 1
                    continue
                if not current_stripped:
                    quote_lines.append("")
                    i += 1
                    continue
                break
            parts.append(f"<blockquote>{_render_blocks(quote_lines)}</blockquote>")
            continue

        if _is_unordered_item(line) or _is_ordered_item(line):
            ordered = _is_ordered_item(line)
            tag = "ol" if ordered else "ul"
            items: list[str] = []
            while i < len(lines):
                current = lines[i]
                if ordered and not _is_ordered_item(current):
                    break
                if not ordered and not _is_unordered_item(current):
                    break
                items.append(f"<li>{render_inline(_strip_list_marker(current))}</li>")
                i += 1
            parts.append(f"<{tag}>{''.join(items)}</{tag}>")
            continue

        paragraph_lines = [stripped]
        i += 1
        while i < len(lines):
            lookahead = lines[i]
            lookahead_stripped = lookahead.strip()
            if not lookahead_stripped:
                break
            if (
                lookahead_stripped.startswith("```")
                or lookahead_stripped.startswith(">")
                or re.match(r"^(#{1,6})\s+", lookahead_stripped)
                or re.match(r"^([-*_])\1{2,}$", lookahead_stripped)
                or _is_unordered_item(lookahead)
                or _is_ordered_item(lookahead)
            ):
                break
            paragraph_lines.append(lookahead_stripped)
            i += 1

        paragraph = " ".join(paragraph_lines)
        parts.append(f"<p>{render_inline(paragraph)}</p>")

    return "\n".join(parts)


def render_markdown_body(markdown: str) -> str:
    return _render_blocks(markdown.splitlines())


def build_html_document(title: str, markdown: str) -> str:
    """Return a styled HTML document for preview/export."""
    body = render_markdown_body(markdown)
    safe_title = escape(title or "博文翻译助手")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{safe_title}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5efe5;
      --surface: rgba(255, 252, 247, 0.92);
      --panel: rgba(255, 255, 255, 0.78);
      --border: rgba(99, 80, 51, 0.16);
      --title: #2d1f12;
      --body: #4a3723;
      --muted: #7d6850;
      --accent: #9a4f19;
      --code-bg: #f3ebe0;
      --quote-bg: #f8f2ea;
      --shadow: 0 22px 60px rgba(88, 54, 18, 0.10);
    }}

    * {{
      box-sizing: border-box;
    }}

    html, body {{
      margin: 0;
      padding: 0;
      background:
        radial-gradient(circle at top left, rgba(202, 120, 48, 0.22), transparent 34%),
        radial-gradient(circle at top right, rgba(138, 95, 54, 0.14), transparent 30%),
        linear-gradient(180deg, #fbf7f1 0%, var(--bg) 100%);
      color: var(--body);
      font-family: "PingFang SC", "Hiragino Sans GB", "Noto Serif CJK SC",
        "Source Han Serif SC", "Songti SC", serif;
      line-height: 1.85;
    }}

    body {{
      padding: 40px 20px 64px;
    }}

    main {{
      width: min(860px, 100%);
      margin: 0 auto;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 28px;
      padding: 48px 56px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(16px);
    }}

    h1, h2, h3, h4, h5, h6 {{
      color: var(--title);
      font-family: "PingFang SC", "SF Pro Display", sans-serif;
      line-height: 1.3;
      letter-spacing: 0.01em;
      margin: 1.7em 0 0.65em;
    }}

    h1 {{
      font-size: 2rem;
      margin-top: 0;
    }}

    h2 {{
      font-size: 1.55rem;
      padding-top: 1.1rem;
      border-top: 1px solid rgba(154, 79, 25, 0.10);
    }}

    p, ul, ol, blockquote, pre {{
      margin: 1em 0;
    }}

    a {{
      color: var(--accent);
      text-decoration: none;
      border-bottom: 1px solid rgba(154, 79, 25, 0.24);
    }}

    strong {{
      color: var(--title);
      font-weight: 700;
    }}

    code {{
      font-family: "SF Mono", "JetBrains Mono", monospace;
      background: var(--code-bg);
      border-radius: 6px;
      padding: 0.15em 0.4em;
      font-size: 0.92em;
    }}

    pre {{
      background: #20150c;
      color: #f8f3ed;
      padding: 18px 20px;
      border-radius: 16px;
      overflow-x: auto;
    }}

    pre code {{
      background: transparent;
      color: inherit;
      padding: 0;
    }}

    blockquote {{
      margin-left: 0;
      padding: 18px 22px;
      background: var(--quote-bg);
      border-left: 4px solid rgba(154, 79, 25, 0.48);
      border-radius: 16px;
      color: var(--muted);
    }}

    ul, ol {{
      padding-left: 1.4rem;
    }}

    li + li {{
      margin-top: 0.45rem;
    }}

    hr {{
      border: none;
      border-top: 1px solid rgba(154, 79, 25, 0.18);
      margin: 2rem 0;
    }}

    img {{
      display: block;
      max-width: 100%;
      border-radius: 18px;
      margin: 1.5rem auto;
      box-shadow: 0 16px 30px rgba(48, 26, 4, 0.12);
    }}

    @media (max-width: 720px) {{
      body {{
        padding: 18px 12px 30px;
      }}

      main {{
        padding: 28px 22px;
        border-radius: 22px;
      }}
    }}
  </style>
</head>
<body>
  <main>
    {body}
  </main>
</body>
</html>
"""
