"""管线封装模块

将翻译管线封装为类，支持异步执行和回调机制。
"""

import sys
import threading
import traceback
from pathlib import Path
from typing import Callable, Optional

# 导入现有管线函数
sys.path.insert(0, str(Path(__file__).parent.parent))
from translate import (
    check_ollama,
    fetch_html,
    extract_metadata,
    html_to_markdown,
    split_into_sections,
    translate_section,
    load_polish_prompt,
    ollama_polish,
    slug_from_url,
)
from core.error_handler import ErrorHandler
from core.image_downloader import download_images
from bs4 import BeautifulSoup
from datetime import date
import yaml
import time


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ARTICLES_DIR = PROJECT_ROOT / "articles"


class TranslatePipeline:
    """翻译管线封装类"""

    def __init__(self, url: str, callbacks: dict):
        """
        初始化管线

        Args:
            url: 文章 URL
            callbacks: 回调函数字典
                - on_progress(percent: int, message: str): 进度更新
                - on_log(message: str): 日志输出
                - on_complete(article_dir: Path): 完成回调
                - on_error(error: Exception, log_path: Path): 错误回调
        """
        self.url = url
        self.on_progress = callbacks.get('progress', lambda p, m: None)
        self.on_log = callbacks.get('log', lambda m: None)
        self.on_complete = callbacks.get('complete', lambda d: None)
        self.on_error = callbacks.get('error', lambda e, p: None)

        self.article_dir: Optional[Path] = None
        self.metadata: Optional[dict] = None

    def run(self):
        """在新线程中运行管线"""
        thread = threading.Thread(target=self._execute)
        thread.daemon = True
        thread.start()

    def _execute(self):
        """执行管线，捕获所有异常"""
        stage = "unknown"
        try:
            # 步骤 0: 检查 Ollama (0%)
            stage = "check_ollama"
            self.on_progress(0, "检查 Ollama...")
            self.on_log("[0/7] 检查 Ollama...")
            if not check_ollama():
                raise RuntimeError("Ollama 服务不可用")
            self.on_log("  Ollama 就绪")

            # 步骤 1: 爬取 (15%)
            stage = "crawl"
            self.on_progress(15, "爬取文章...")
            self.on_log(f"[1/7] 爬取文章: {self.url}")
            html_content = fetch_html(self.url)
            soup = BeautifulSoup(html_content, "html.parser")
            self.on_log("  爬取成功")

            # 步骤 2: 提取元数据 (25%)
            stage = "metadata"
            self.on_progress(25, "提取元数据...")
            self.on_log("[2/7] 提取元数据...")
            self.metadata = extract_metadata(soup, self.url)
            slug = slug_from_url(self.url)
            self.article_dir = ARTICLES_DIR / f"{date.today().isoformat()}-{slug}"
            self.article_dir.mkdir(parents=True, exist_ok=True)

            self.on_log(f"  标题: {self.metadata['title']}")
            self.on_log(f"  作者: {self.metadata['author']}")
            self.on_log(f"  目录: {self.article_dir.name}")

            # 步骤 3: 转换 Markdown (35%)
            stage = "convert"
            self.on_progress(35, "转换为 Markdown...")
            self.on_log("[3/7] 转换为 Markdown...")
            original_md = html_to_markdown(html_content)

            # 下载图片
            self.on_log("  下载图片...")
            original_md = download_images(original_md, self.article_dir, self.url)

            original_path = self.article_dir / "original.md"
            original_path.write_text(
                f"# {self.metadata['title']}\n\n{original_md}",
                encoding="utf-8"
            )

            # 保存 metadata
            meta_path = self.article_dir / "metadata.yaml"
            with open(meta_path, "w", encoding="utf-8") as f:
                yaml.dump(self.metadata, f, allow_unicode=True, default_flow_style=False)

            # 步骤 4: 拆分章节 (45%)
            self.on_progress(45, "拆分章节...")
            self.on_log("[4/7] 拆分章节...")
            sections = split_into_sections(original_md)
            self.on_log(f"  共 {len(sections)} 个章节")

            # 步骤 5: Google Translate 翻译 (50-70%)
            stage = "translate"
            self.on_log("[5/7] Google Translate 翻译...")
            translated_sections = []
            for i, section in enumerate(sections):
                progress = 50 + int((i / len(sections)) * 20)
                self.on_progress(progress, f"翻译章节 {i+1}/{len(sections)}...")

                heading_preview = (
                    section["heading"][:40] if section["heading"] else "(开头)"
                )
                self.on_log(f"  翻译章节 {i + 1}/{len(sections)}: {heading_preview}")
                translated_sections.append(translate_section(section))
                time.sleep(0.5)

            # 拼接原文和翻译
            full_original = "\n\n".join(
                f"{s['original_heading']}\n\n{s['original_body']}"
                for s in translated_sections
            )
            full_translated = "\n\n".join(
                f"{s['heading']}\n\n{s['body']}" for s in translated_sections
            )

            # 保存机翻中间文件
            raw_translated_path = self.article_dir / "raw_translated.md"
            raw_translated_path.write_text(full_translated, encoding="utf-8")
            self.on_log(f"  机翻中间文件: {raw_translated_path.name}")

            # 步骤 6: Ollama 润色 (75-95%)
            stage = "polish"
            self.on_progress(75, "Ollama 润色排版...")
            self.on_log("[6/7] Ollama 润色排版...")
            system_prompt = load_polish_prompt()

            try:
                polished = ollama_polish(
                    system_prompt,
                    full_original,
                    full_translated,
                    self.metadata
                )

                if not polished:
                    raise RuntimeError("润色返回空结果")

            except Exception as polish_error:
                self.on_log(f"  [警告] 润色失败: {polish_error}")
                self.on_log("  [降级] 使用 Google Translate 机翻结果")

                # 降级到机翻结果
                polished = full_translated

                # 记录润色失败日志
                ErrorHandler.log_error(
                    polish_error,
                    {
                        'url': self.url,
                        'article_dir': str(self.article_dir),
                    },
                    stage="polish"
                )

            # 步骤 7: 保存结果 (100%)
            self.on_progress(95, "保存结果...")
            self.on_log("[7/7] 保存结果...")
            translated_path = self.article_dir / "translated.md"
            translated_path.write_text(polished, encoding="utf-8")

            # 更新状态
            self.metadata["status"] = "translated"
            with open(meta_path, "w", encoding="utf-8") as f:
                yaml.dump(self.metadata, f, allow_unicode=True, default_flow_style=False)

            self.on_progress(100, "完成！")
            self.on_log(f"\n完成! 文件保存在: {self.article_dir}")
            self.on_log(f"  原文:     {original_path.name}")
            self.on_log(f"  机翻中间: {raw_translated_path.name}")
            self.on_log(f"  润色翻译: {translated_path.name}")

            # 调用完成回调
            self.on_complete(self.article_dir)

        except Exception as e:
            # 记录错误日志
            log_path = ErrorHandler.log_error(
                e,
                {
                    'url': self.url,
                    'article_dir': str(self.article_dir) if self.article_dir else 'N/A',
                },
                stage=stage
            )

            # 调用错误回调
            self.on_error(e, log_path)
