"""Content storage helpers for the SwiftUI app worker."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import json

import yaml

from worker.markdown_renderer import build_html_document


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class ContentPaths:
    root: Path

    @property
    def articles_dir(self) -> Path:
        return self.root / "articles"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"

    @property
    def errors_dir(self) -> Path:
        return self.logs_dir / "errors"

    def ensure(self):
        self.articles_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.errors_dir.mkdir(parents=True, exist_ok=True)


def default_storage_root() -> Path:
    return Path(__file__).resolve().parents[2]


class ArticleStore:
    """Manage article metadata and translated artifacts under a storage root."""

    def __init__(self, storage_root: Path | str | None = None):
        self.set_storage_root(storage_root or default_storage_root())

    def set_storage_root(self, storage_root: Path | str):
        root = Path(storage_root).expanduser().resolve()
        self.paths = ContentPaths(root)
        self.paths.ensure()

    def summary_payload(self) -> dict[str, Any]:
        return {
            "storageRoot": str(self.paths.root),
            "articlesDir": str(self.paths.articles_dir),
            "logsDir": str(self.paths.logs_dir),
        }

    def resolve_article_dir(self, article_id: str) -> Path:
        article_dir = (self.paths.articles_dir / article_id).resolve()
        if article_dir.parent != self.paths.articles_dir.resolve():
            raise ValueError("非法 articleId")
        if not article_dir.exists():
            raise FileNotFoundError(f"文章不存在: {article_id}")
        return article_dir

    def create_article_dir(self, base_name: str) -> Path:
        candidate = self.paths.articles_dir / base_name
        if not candidate.exists():
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate

        index = 2
        while True:
            next_candidate = self.paths.articles_dir / f"{base_name}-{index}"
            if not next_candidate.exists():
                next_candidate.mkdir(parents=True, exist_ok=True)
                return next_candidate
            index += 1

    def find_by_source_url(self, url: str) -> list[dict[str, Any]]:
        """Return summaries of articles whose source URL matches *url*."""
        matches: list[dict[str, Any]] = []
        for meta_path in self.paths.articles_dir.glob("*/metadata.yaml"):
            try:
                meta = self._load_metadata(meta_path.parent)
            except Exception:
                continue
            if meta.get("source", "") == url:
                matches.append(self._load_summary(meta_path.parent))
        return matches

    def list_articles(
        self,
        status: str | None = None,
        search: str | None = None,
        sort: str | None = "added_desc",
    ) -> list[dict[str, Any]]:
        articles: list[dict[str, Any]] = []
        search_term = search.casefold().strip() if search else None

        for meta_path in self.paths.articles_dir.glob("*/metadata.yaml"):
            try:
                article = self._load_summary(meta_path.parent)
            except Exception:
                continue

            if status and article.get("status") != status:
                continue

            if search_term:
                haystack = " ".join(
                    [
                        article.get("title", ""),
                        article.get("author", ""),
                        article.get("sourceURL", ""),
                    ]
                ).casefold()
                if search_term not in haystack:
                    continue

            articles.append(article)

        reverse = sort != "added_asc"
        articles.sort(key=lambda item: item.get("added", ""), reverse=reverse)
        return articles

    def get_article(self, article_id: str) -> dict[str, Any]:
        article_dir = self.resolve_article_dir(article_id)
        summary = self._load_summary(article_dir)
        translated_markdown = self._read_optional(article_dir / "translated.md")
        html_path = article_dir / "translated.html"

        if translated_markdown:
            self.export_article_html(article_id)

        return {
            **summary,
            "originalMarkdown": self._read_optional(article_dir / "original.md"),
            "rawTranslatedMarkdown": self._read_optional(article_dir / "raw_translated.md"),
            "translatedMarkdown": translated_markdown,
            "htmlPath": str(html_path) if html_path.exists() else None,
            "images": self._collect_images(article_dir),
        }

    def save_translated_markdown(self, article_id: str, markdown: str) -> dict[str, Any]:
        article_dir = self.resolve_article_dir(article_id)
        translated_path = article_dir / "translated.md"
        translated_path.write_text(markdown, encoding="utf-8")

        html_result = self.export_article_html(article_id)
        return {
            "articleId": article_id,
            "savedAt": _now_iso(),
            "translatedPath": str(translated_path),
            "htmlPath": html_result["htmlPath"],
        }

    def update_status(self, article_id: str, status: str) -> dict[str, Any]:
        if status not in {"pending", "translated", "published", "failed"}:
            raise ValueError(f"不支持的状态: {status}")

        article_dir = self.resolve_article_dir(article_id)
        metadata = self._load_metadata(article_dir)
        metadata["status"] = status
        self._write_metadata(article_dir, metadata)

        return {
            "articleId": article_id,
            "status": status,
            "updatedAt": _now_iso(),
        }

    def delete_article(self, article_id: str) -> dict[str, Any]:
        import shutil
        article_dir = self.resolve_article_dir(article_id)
        shutil.rmtree(article_dir)
        return {"articleId": article_id, "deleted": True}

    def export_article_html(self, article_id: str) -> dict[str, Any]:
        article_dir = self.resolve_article_dir(article_id)
        metadata = self._load_metadata(article_dir)
        markdown = self._read_optional(article_dir / "translated.md")
        html = build_html_document(metadata.get("title", "博文翻译助手"), markdown)
        html_path = article_dir / "translated.html"
        html_path.write_text(html, encoding="utf-8")
        return {
            "articleId": article_id,
            "htmlPath": str(html_path),
            "updatedAt": _now_iso(),
        }

    def write_error_report(
        self,
        error: Exception,
        context: dict[str, Any],
        stage: str,
        traceback_text: str,
    ) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = self.paths.errors_dir / f"{timestamp}.log"
        json_path = self.paths.errors_dir / f"{timestamp}.json"

        text_report = "\n".join(
            [
                "=== 翻译失败报告 ===",
                f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"失败阶段: {stage}",
                f"错误类型: {type(error).__name__}",
                f"错误详情: {error}",
                "",
                "--- 上下文 ---",
                *(f"{key}: {value}" for key, value in context.items()),
                "",
                "--- 堆栈跟踪 ---",
                traceback_text,
            ]
        )
        log_path.write_text(text_report, encoding="utf-8")

        json_report = {
            "timestamp": _now_iso(),
            "stage": stage,
            "errorType": type(error).__name__,
            "errorMessage": str(error),
            "context": context,
            "traceback": traceback_text,
        }
        json_path.write_text(
            json.dumps(json_report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(log_path)

    def _load_summary(self, article_dir: Path) -> dict[str, Any]:
        metadata = self._load_metadata(article_dir)
        html_path = article_dir / "translated.html"
        return {
            "id": article_dir.name,
            "title": metadata.get("title", "Untitled"),
            "author": metadata.get("author", "Unknown"),
            "added": metadata.get("added", ""),
            "date": metadata.get("date", ""),
            "status": metadata.get("status", "pending"),
            "sourceURL": metadata.get("source", ""),
            "directoryPath": str(article_dir),
            "htmlPath": str(html_path) if html_path.exists() else None,
        }

    def _load_metadata(self, article_dir: Path) -> dict[str, Any]:
        meta_path = article_dir / "metadata.yaml"
        if not meta_path.exists():
            raise FileNotFoundError(f"缺少 metadata.yaml: {article_dir.name}")

        with open(meta_path, encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    def _write_metadata(self, article_dir: Path, metadata: dict[str, Any]):
        meta_path = article_dir / "metadata.yaml"
        with open(meta_path, "w", encoding="utf-8") as handle:
            yaml.dump(metadata, handle, allow_unicode=True, default_flow_style=False)

    def _read_optional(self, path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def _collect_images(self, article_dir: Path) -> list[str]:
        images: list[str] = []
        for candidate in article_dir.rglob("*"):
            if candidate.is_file() and candidate.suffix.lower() in IMAGE_EXTENSIONS:
                images.append(str(candidate))
        return sorted(images)
