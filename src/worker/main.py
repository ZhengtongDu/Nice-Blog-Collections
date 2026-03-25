#!/usr/bin/env python3
"""JSON-lines worker that powers the SwiftUI macOS app."""

from __future__ import annotations

from pathlib import Path
import json
import os
import sys
import threading
import uuid


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from worker.content_store import ArticleStore, default_storage_root
from worker.translation_job import TranslationJob, probe_ollama
from worker.link_discovery import discover_links
from worker.batch_job import BatchTranslationJob


class WorkerServer:
    def __init__(self):
        storage_root = Path(
            os.environ.get("BLOG_TRANSLATOR_STORAGE_ROOT", default_storage_root())
        )
        self.store = ArticleStore(storage_root)
        self._write_lock = threading.Lock()
        self._active_job: TranslationJob | None = None
        self._active_batch: BatchTranslationJob | None = None

    def run(self):
        for raw_line in sys.stdin:
            line = raw_line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
            except json.JSONDecodeError as error:
                self._write(
                    {
                        "type": "response",
                        "id": None,
                        "ok": False,
                        "error": {"message": f"非法 JSON: {error}"},
                    }
                )
                continue

            request_id = request.get("id")
            command = request.get("command")
            params = request.get("params", {})

            try:
                result = self._dispatch(command, params)
                self._write(
                    {
                        "type": "response",
                        "id": request_id,
                        "ok": True,
                        "result": result,
                    }
                )
            except Exception as error:
                self._write(
                    {
                        "type": "response",
                        "id": request_id,
                        "ok": False,
                        "error": {"message": str(error)},
                    }
                )

    def _dispatch(self, command: str, params: dict):
        if command == "health_check":
            health = probe_ollama(test_generate=False)
            return {
                **self.store.summary_payload(),
                "workerReady": True,
                "ollamaReachable": health["ollamaReachable"],
                "modelInstalled": health["modelInstalled"],
                "lastError": health["message"],
            }

        if command == "set_storage_root":
            path = params.get("path")
            if not path:
                raise ValueError("缺少 path 参数")
            self.store.set_storage_root(path)
            health = self._dispatch("health_check", {})
            self._send_event("articles_changed", {"reason": "storage_root_updated"})
            return health

        if command == "check_duplicate":
            url = (params.get("url") or "").strip()
            if not url:
                raise ValueError("缺少 url 参数")
            matches = self.store.find_by_source_url(url)
            return {"url": url, "duplicates": matches}

        if command == "start_translation":
            if self._active_job and self._active_job.thread.is_alive():
                raise RuntimeError("当前已有翻译任务正在进行中")
            if self._active_batch and self._active_batch.thread.is_alive():
                raise RuntimeError("当前已有批量翻译任务正在进行中")
            url = (params.get("url") or "").strip()
            if not url.startswith("http"):
                raise ValueError("URL 必须以 http:// 或 https:// 开头")

            job = TranslationJob(
                job_id=str(uuid.uuid4()),
                url=url,
                store=self.store,
                send_event=self._send_event,
                on_finish=self._clear_active_job,
            )
            self._active_job = job
            job.start()
            return job.snapshot.as_payload()

        if command == "cancel_job":
            job_id = params.get("jobId")
            if not self._active_job or self._active_job.job_id != job_id:
                raise RuntimeError("未找到对应任务")
            self._active_job.cancel()
            return {"jobId": job_id, "accepted": True}

        if command == "list_articles":
            return self.store.list_articles(
                status=params.get("status"),
                search=params.get("search"),
                sort=params.get("sort", "added_desc"),
            )

        if command == "get_article":
            article_id = params.get("articleId")
            if not article_id:
                raise ValueError("缺少 articleId 参数")
            return self.store.get_article(article_id)

        if command == "save_translated_markdown":
            article_id = params.get("articleId")
            markdown = params.get("markdown", "")
            if not article_id:
                raise ValueError("缺少 articleId 参数")
            result = self.store.save_translated_markdown(article_id, markdown)
            self._send_event("article_saved", result)
            self._send_event("articles_changed", {"reason": "article_saved"})
            return result

        if command == "update_status":
            article_id = params.get("articleId")
            status = params.get("status")
            if not article_id or not status:
                raise ValueError("缺少 articleId 或 status 参数")
            result = self.store.update_status(article_id, status)
            self._send_event("articles_changed", {"reason": "status_updated"})
            return result

        if command == "delete_article":
            article_id = params.get("articleId")
            if not article_id:
                raise ValueError("缺少 articleId 参数")
            result = self.store.delete_article(article_id)
            self._send_event("articles_changed", {"reason": "article_deleted"})
            return result

        if command == "discover_links":
            url = (params.get("url") or "").strip()
            if not url.startswith("http"):
                raise ValueError("URL 必须以 http:// 或 https:// 开头")
            return discover_links(url, self.store)

        if command == "start_batch_translation":
            if self._active_job and self._active_job.thread.is_alive():
                raise RuntimeError("当前已有翻译任务正在进行中")
            if self._active_batch and self._active_batch.thread.is_alive():
                raise RuntimeError("当前已有批量翻译任务正在进行中")
            urls = params.get("urls", [])
            if not urls:
                raise ValueError("缺少 urls 参数")
            batch = BatchTranslationJob(
                batch_id=str(uuid.uuid4()),
                urls=urls,
                store=self.store,
                send_event=self._send_event,
                on_finish=self._clear_active_batch,
                series_title=params.get("seriesTitle"),
                parent_url=params.get("parentURL"),
            )
            self._active_batch = batch
            batch.start()
            return {
                "batchId": batch.batch_id,
                "totalJobs": batch.total_jobs,
                "state": "running",
            }

        if command == "cancel_batch":
            batch_id = params.get("batchId")
            if not self._active_batch or self._active_batch.batch_id != batch_id:
                raise RuntimeError("未找到对应批量任务")
            self._active_batch.cancel()
            return {"batchId": batch_id, "accepted": True}

        if command == "export_article_html":
            article_id = params.get("articleId")
            if not article_id:
                raise ValueError("缺少 articleId 参数")
            result = self.store.export_article_html(article_id)
            self._send_event("html_exported", result)
            return result

        raise ValueError(f"未知命令: {command}")

    def _send_event(self, event: str, payload: dict):
        self._write({"type": "event", "event": event, "payload": payload})

    def _write(self, message: dict):
        with self._write_lock:
            sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
            sys.stdout.flush()

    def _clear_active_job(self, job_id: str):
        if self._active_job and self._active_job.job_id == job_id:
            self._active_job = None

    def _clear_active_batch(self, batch_id: str):
        if self._active_batch and self._active_batch.batch_id == batch_id:
            self._active_batch = None


def main():
    WorkerServer().run()


if __name__ == "__main__":
    main()
