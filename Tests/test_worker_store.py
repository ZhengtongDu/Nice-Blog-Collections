from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from worker.content_store import ArticleStore
from worker.markdown_renderer import build_html_document


class ArticleStoreTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.store = ArticleStore(self.root)
        article_dir = self.root / "articles" / "2026-03-24-demo"
        article_dir.mkdir(parents=True, exist_ok=True)
        with open(article_dir / "metadata.yaml", "w", encoding="utf-8") as handle:
            yaml.dump(
                {
                    "title": "Demo",
                    "author": "Tester",
                    "added": "2026-03-24",
                    "date": "2026-03-24",
                    "status": "translated",
                    "source": "https://example.com/post",
                },
                handle,
                allow_unicode=True,
                default_flow_style=False,
            )
        (article_dir / "translated.md").write_text(
            "## 标题\n\n这是 **正文**。\n\n- 一\n- 二\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_list_and_get_article(self):
        articles = self.store.list_articles(status="translated")
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["title"], "Demo")

        detail = self.store.get_article("2026-03-24-demo")
        self.assertIn("translatedMarkdown", detail)
        self.assertTrue(detail["translatedMarkdown"].startswith("## 标题"))

    def test_save_and_export_html(self):
        result = self.store.save_translated_markdown(
            "2026-03-24-demo",
            "## 新标题\n\n这里有 `code`。",
        )
        html_path = Path(result["htmlPath"])
        self.assertTrue(html_path.exists())
        self.assertIn("<code>code</code>", html_path.read_text(encoding="utf-8"))

    def test_update_status(self):
        result = self.store.update_status("2026-03-24-demo", "published")
        self.assertEqual(result["status"], "published")
        detail = self.store.get_article("2026-03-24-demo")
        self.assertEqual(detail["status"], "published")


class MarkdownRendererTests(unittest.TestCase):
    def test_document_contains_blockquote_and_list(self):
        html = build_html_document(
            "Title",
            "> 引用\n\n## 节标题\n\n- 项目一\n- 项目二\n",
        )
        self.assertIn("<blockquote>", html)
        self.assertIn("<h2>节标题</h2>", html)
        self.assertIn("<ul>", html)

    def test_inline_tokens_do_not_leak_to_html(self):
        html = build_html_document(
            "Title",
            "这里有 `code` 和 [链接](https://example.com) 以及 **强调**。",
        )
        self.assertNotIn("TOKENPLACEHOLDER", html)
        self.assertIn("<code>code</code>", html)
        self.assertIn('<a href="https://example.com">链接</a>', html)


if __name__ == "__main__":
    unittest.main()
