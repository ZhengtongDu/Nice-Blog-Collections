"""Batch translation job — translates multiple URLs sequentially."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from threading import Event, Thread
from typing import Any, Callable
import traceback

from worker.content_store import ArticleStore
from worker.translation_job import JobCancelled, run_single_translation


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class BatchTranslationJob:
    """Translate a list of URLs one by one, emitting batch-level events."""

    def __init__(
        self,
        batch_id: str,
        urls: list[str],
        store: ArticleStore,
        send_event: Callable[[str, dict[str, Any]], None],
        on_finish: Callable[[str], None],
        series_title: str | None = None,
        parent_url: str | None = None,
    ):
        self.batch_id = batch_id
        self.urls = urls
        self.store = store
        self.send_event = send_event
        self.on_finish = on_finish
        self.series_title = series_title
        self.parent_url = parent_url
        self.cancel_event = Event()
        self.thread = Thread(
            target=self._run, name=f"batch-job-{batch_id}", daemon=True
        )

        self.total_jobs = len(urls)
        self.current_index = 0
        self.succeeded = 0
        self.failed = 0
        self.article_ids: list[str] = []

    def start(self):
        self.send_event("batch_progress", self._snapshot("running"))
        self.thread.start()

    def cancel(self):
        self.cancel_event.set()

    def _snapshot(self, state: str, current_url: str | None = None, title: str | None = None) -> dict:
        return {
            "batchId": self.batch_id,
            "totalJobs": self.total_jobs,
            "currentIndex": self.current_index,
            "state": state,
            "currentURL": current_url,
            "currentArticleTitle": title,
            "succeeded": self.succeeded,
            "failed": self.failed,
        }

    def _run(self):
        try:
            self._execute_batch()
        except JobCancelled:
            pass
        finally:
            # Write series relationships if we have results
            if self.series_title and self.article_ids:
                self._write_series_metadata()

            state = "cancelled" if self.cancel_event.is_set() else "completed"
            self.send_event("batch_completed", {
                "batchId": self.batch_id,
                "totalJobs": self.total_jobs,
                "succeeded": self.succeeded,
                "failed": self.failed,
                "articleIds": self.article_ids,
                "state": state,
            })
            self.send_event("articles_changed", {"reason": "batch_completed"})
            self.on_finish(self.batch_id)

    def _execute_batch(self):
        for index, url in enumerate(self.urls):
            if self.cancel_event.is_set():
                raise JobCancelled()

            self.current_index = index + 1
            self.send_event("batch_progress", self._snapshot(
                "running", current_url=url, title=f"文章 {self.current_index}/{self.total_jobs}",
            ))

            try:
                article_dir = run_single_translation(
                    url=url,
                    store=self.store,
                    advance=self._make_advance(index),
                    log=self._make_log(),
                    ensure_not_cancelled=self._ensure_not_cancelled,
                )
                self.succeeded += 1
                self.article_ids.append(article_dir.name)
            except JobCancelled:
                raise
            except Exception as error:
                self.failed += 1
                trace = traceback.format_exc()
                self.store.write_error_report(
                    error,
                    {"url": url, "batchId": self.batch_id},
                    stage="batch_item",
                    traceback_text=trace,
                )
                self.send_event("job_log", {
                    "jobId": self.batch_id,
                    "timestamp": _now_iso(),
                    "line": f"[失败] {url}: {error}",
                })

    def _make_advance(self, batch_index: int):
        """Create an advance callback that maps per-article progress to batch events."""
        def advance(stage: str, percent: int, message: str):
            self.send_event("batch_job_progress", {
                "batchId": self.batch_id,
                "currentIndex": batch_index + 1,
                "totalJobs": self.total_jobs,
                "stage": stage,
                "percent": percent,
                "message": message,
            })
        return advance

    def _make_log(self):
        def log(line: str):
            self.send_event("job_log", {
                "jobId": self.batch_id,
                "timestamp": _now_iso(),
                "line": line,
            })
        return log

    def _ensure_not_cancelled(self):
        if self.cancel_event.is_set():
            raise JobCancelled()

    def _write_series_metadata(self):
        """Write parent/children/series fields to metadata.yaml files."""
        # Find or create parent article entry
        parent_id = None
        if self.parent_url:
            matches = self.store.find_by_source_url(self.parent_url)
            if matches:
                parent_id = matches[0]["id"]

        self.store.update_series_metadata(
            parent_id=parent_id,
            child_ids=self.article_ids,
            series_title=self.series_title or "",
        )
