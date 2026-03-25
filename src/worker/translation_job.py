"""Background translation job for the worker protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from threading import Event, Thread
from typing import Any, Callable
import re
import sys
import traceback
import time

import requests
import yaml
from bs4 import BeautifulSoup

if sys.version_info >= (3, 13) and "cgi" not in sys.modules:
    import html

if sys.version_info >= (3, 13):
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

from config import OLLAMA_BASE_URL, OLLAMA_MODEL, POLISH_TIMEOUT
from core.image_downloader import download_images
from translate import (
    extract_metadata,
    fetch_html,
    html_to_markdown,
    load_polish_prompt,
    slug_from_url,
    split_into_sections,
    translate_section,
)
from worker.content_store import ArticleStore


class JobCancelled(Exception):
    """Raised when a running translation job is cancelled."""


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def probe_ollama(test_generate: bool = False) -> dict[str, Any]:
    """Return reachability/model information for the configured Ollama."""
    try:
        tags_response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        tags_response.raise_for_status()
        models = [model["name"] for model in tags_response.json().get("models", [])]
        model_installed = OLLAMA_MODEL in models

        if test_generate and model_installed:
            generate_response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": "hi",
                    "stream": False,
                    "think": False,
                    "options": {"num_predict": 4},
                },
                timeout=60,
            )
            generate_response.raise_for_status()
            output = generate_response.json().get("response", "").strip()
            if not output:
                return {
                    "ollamaReachable": True,
                    "modelInstalled": model_installed,
                    "message": f"{OLLAMA_MODEL} 生成测试返回空结果",
                }

        return {
            "ollamaReachable": True,
            "modelInstalled": model_installed,
            "message": None if model_installed else f"未找到模型 {OLLAMA_MODEL}",
        }
    except requests.ConnectionError:
        return {
            "ollamaReachable": False,
            "modelInstalled": False,
            "message": f"无法连接 Ollama: {OLLAMA_BASE_URL}",
        }
    except Exception as error:
        return {
            "ollamaReachable": False,
            "modelInstalled": False,
            "message": str(error),
        }


@dataclass
class JobSnapshot:
    job_id: str
    url: str
    stage: str = "idle"
    percent: int = 0
    state: str = "queued"
    start_time: str = field(default_factory=_now_iso)
    end_time: str | None = None
    message: str = ""
    log_items: list[str] = field(default_factory=list)
    output_directory: str | None = None
    error_summary: str | None = None

    def as_payload(self) -> dict[str, Any]:
        return {
            "jobId": self.job_id,
            "url": self.url,
            "stage": self.stage,
            "percent": self.percent,
            "state": self.state,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "message": self.message,
            "logItems": list(self.log_items),
            "outputDirectory": self.output_directory,
            "errorSummary": self.error_summary,
        }


class TranslationJob:
    """Run the existing Python translation pipeline behind worker events."""

    def __init__(
        self,
        job_id: str,
        url: str,
        store: ArticleStore,
        send_event: Callable[[str, dict[str, Any]], None],
        on_finish: Callable[[str], None],
    ):
        self.job_id = job_id
        self.url = url
        self.store = store
        self.send_event = send_event
        self.on_finish = on_finish
        self.cancel_event = Event()
        self.snapshot = JobSnapshot(job_id=job_id, url=url)
        self.thread = Thread(target=self._run, name=f"translation-job-{job_id}", daemon=True)

    def start(self):
        self.snapshot.state = "running"
        self.send_event("job_started", self.snapshot.as_payload())
        self.thread.start()

    def cancel(self):
        self.cancel_event.set()

    def _run(self):
        try:
            article_dir = self._execute_pipeline()
            self.snapshot.state = "completed"
            self.snapshot.stage = "save"
            self.snapshot.percent = 100
            self.snapshot.message = "翻译完成"
            self.snapshot.end_time = _now_iso()
            self.snapshot.output_directory = str(article_dir)
            self.send_event("job_completed", self.snapshot.as_payload())
            self.send_event("articles_changed", {"reason": "translation_completed"})
        except JobCancelled:
            self.snapshot.state = "cancelled"
            self.snapshot.message = "任务已取消"
            self.snapshot.end_time = _now_iso()
            self.send_event("job_completed", self.snapshot.as_payload())
        except Exception as error:
            trace = traceback.format_exc()
            log_path = self.store.write_error_report(
                error,
                {
                    "url": self.url,
                    "jobId": self.job_id,
                    "outputDirectory": self.snapshot.output_directory,
                },
                stage=self.snapshot.stage,
                traceback_text=trace,
            )
            self.snapshot.state = "failed"
            self.snapshot.error_summary = str(error)
            self.snapshot.message = "翻译失败"
            self.snapshot.end_time = _now_iso()
            self.send_event(
                "job_error",
                {
                    "jobId": self.job_id,
                    "stage": self.snapshot.stage,
                    "message": str(error),
                    "logPath": log_path,
                },
            )
            self.send_event("job_completed", self.snapshot.as_payload())
        finally:
            self.on_finish(self.job_id)

    def _execute_pipeline(self) -> Path:
        def _set_output_dir(path: str):
            self.snapshot.output_directory = path

        return run_single_translation(
            url=self.url,
            store=self.store,
            advance=self._advance,
            log=self._log,
            ensure_not_cancelled=self._ensure_not_cancelled,
            output_dir_callback=_set_output_dir,
        )

    def _advance(self, stage: str, percent: int, message: str):
        self.snapshot.stage = stage
        self.snapshot.percent = percent
        self.snapshot.message = message
        self.send_event("job_progress", self.snapshot.as_payload())
        self._log(message)

    def _log(self, line: str):
        self.snapshot.log_items.append(line)
        if len(self.snapshot.log_items) > 500:
            self.snapshot.log_items = self.snapshot.log_items[-500:]
        self.send_event(
            "job_log",
            {
                "jobId": self.job_id,
                "timestamp": _now_iso(),
                "line": line,
            },
        )

    def _ensure_not_cancelled(self):
        if self.cancel_event.is_set():
            raise JobCancelled()


def run_single_translation(
    url: str,
    store: ArticleStore,
    advance: Callable[[str, int, str], None],
    log: Callable[[str], None],
    ensure_not_cancelled: Callable[[], None],
    output_dir_callback: Callable[[str], None] | None = None,
) -> Path:
    """Execute the full translation pipeline for a single URL.

    This is the shared core used by both TranslationJob (single) and
    BatchTranslationJob (batch).
    """
    advance("check_ollama", 2, "检查 Ollama 与模型状态")
    health = probe_ollama(test_generate=False)
    if not health["ollamaReachable"]:
        raise RuntimeError(health["message"] or "Ollama 服务不可用")
    if not health["modelInstalled"]:
        raise RuntimeError(health["message"] or f"未安装模型 {OLLAMA_MODEL}")
    log("Ollama 就绪")

    ensure_not_cancelled()
    advance("fetch", 12, f"爬取文章: {url}")
    html_content = fetch_html(url)
    soup = BeautifulSoup(html_content, "html.parser")
    log("网页抓取完成")

    ensure_not_cancelled()
    advance("extract_metadata", 24, "提取文章元数据")
    metadata = extract_metadata(soup, url)
    slug = slug_from_url(url)
    article_dir = store.create_article_dir(f"{date.today().isoformat()}-{slug}")
    if output_dir_callback:
        output_dir_callback(str(article_dir))
    log(f"文章目录: {article_dir.name}")
    log(f"标题: {metadata.get('title', 'Untitled')}")
    log(f"作者: {metadata.get('author', 'Unknown')}")

    ensure_not_cancelled()
    advance("convert", 36, "转换原文为 Markdown 并下载图片")
    original_md = html_to_markdown(html_content)
    original_md = download_images(original_md, article_dir, url)

    original_path = article_dir / "original.md"
    original_path.write_text(f"# {metadata['title']}\n\n{original_md}", encoding="utf-8")

    metadata["status"] = "pending"
    meta_path = article_dir / "metadata.yaml"
    with open(meta_path, "w", encoding="utf-8") as handle:
        yaml.dump(metadata, handle, allow_unicode=True, default_flow_style=False)

    ensure_not_cancelled()
    sections = split_into_sections(original_md)
    if not sections:
        raise RuntimeError("文章正文为空，无法翻译")

    advance("translate", 45, f"分段翻译，共 {len(sections)} 段")
    translated_sections: list[dict[str, str]] = []

    for index, section in enumerate(sections, start=1):
        ensure_not_cancelled()
        ratio = index / max(len(sections), 1)
        percent = 45 + int(ratio * 25)
        heading_preview = section["heading"][:40] if section["heading"] else "(开头)"
        advance("translate", percent, f"翻译章节 {index}/{len(sections)}: {heading_preview}")
        translated_sections.append(translate_section(section))
        time.sleep(0.2)

    full_original = "\n\n".join(
        f"{section['original_heading']}\n\n{section['original_body']}"
        for section in translated_sections
    )
    full_translated = "\n\n".join(
        f"{section['heading']}\n\n{section['body']}" for section in translated_sections
    )

    raw_translated_path = article_dir / "raw_translated.md"
    raw_translated_path.write_text(full_translated, encoding="utf-8")

    ensure_not_cancelled()
    advance("polish", 76, "使用 Ollama 润色与排版")
    system_prompt = load_polish_prompt()
    polished = _polish_sections_standalone(
        system_prompt, full_original, full_translated, metadata,
        advance, log, ensure_not_cancelled,
    )

    ensure_not_cancelled()
    advance("save", 92, "保存翻译结果与 HTML 预览")
    translated_path = article_dir / "translated.md"
    translated_path.write_text(polished, encoding="utf-8")
    metadata["status"] = "translated"
    with open(meta_path, "w", encoding="utf-8") as handle:
        yaml.dump(metadata, handle, allow_unicode=True, default_flow_style=False)
    store.export_article_html(article_dir.name)

    log(f"原文: {original_path.name}")
    log(f"机翻: {raw_translated_path.name}")
    log(f"润色翻译: {translated_path.name}")
    return article_dir


def _polish_sections_standalone(
    system_prompt: str,
    original: str,
    translated: str,
    metadata: dict[str, Any],
    advance: Callable,
    log: Callable,
    ensure_not_cancelled: Callable,
) -> str:
    """Polish translated text section by section using Ollama."""
    meta_header = (
        f"- 原文标题：{metadata.get('title', '')}\n"
        f"- 作者：{metadata.get('author', '')}\n"
        f"- 原文链接：{metadata.get('source', '')}"
    )

    original_sections = re.split(r"(?=^## )", original, flags=re.MULTILINE)
    translated_sections = re.split(r"(?=^## )", translated, flags=re.MULTILINE)

    if len(original_sections) != len(translated_sections):
        original_sections = [original]
        translated_sections = [translated]

    polished_parts: list[str] = []
    total = len(original_sections)

    for index, (original_section, translated_section) in enumerate(
        zip(original_sections, translated_sections),
        start=1,
    ):
        ensure_not_cancelled()
        if not original_section.strip():
            continue

        progress = 76 + int((index / max(total, 1)) * 14)
        advance("polish", progress, f"润色章节 {index}/{total}")

        instructions: list[str] = []
        if index == 1:
            instructions.append("这是文章的第一部分，请在开头添加著作权声明和摘要。")
        if index == total:
            instructions.append("这是文章的最后一部分，请在末尾添加译者总结。")
        if index != 1 and index != total:
            instructions.append("这是文章的中间部分，不需要添加著作权声明、摘要或译者总结。")

        instructions_text = '\n'.join(instructions)
        user_prompt = (
            "请按照系统提示中的规则润色以下章节。\n\n"
            f"## 文章元数据\n{meta_header}\n\n"
            f"## 位置说明\n{instructions_text}\n\n"
            f"## 英文原文\n{original_section.strip()}\n\n"
            f"## Google Translate 机翻结果\n{translated_section.strip()}\n\n"
            "请输出润色后的内容（Markdown 格式）："
        )

        try:
            response = requests.post(
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
            response.raise_for_status()
            part = response.json().get("response", "").strip()
            polished_parts.append(part or translated_section.strip())
        except Exception as error:
            log(f"[警告] 润色章节 {index} 失败，降级为机翻结果: {error}")
            polished_parts.append(translated_section.strip())

    return "\n\n".join(polished_parts).strip()
