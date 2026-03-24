"""翻译管线 UI 界面"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from gui.widgets import LogTextWidget, ErrorPanel, ProgressFrame
from core.pipeline import TranslatePipeline
from config import LOG_MAX_LINES


class TranslateTab(tk.Frame):
    """翻译管线界面"""

    def __init__(self, parent):
        super().__init__(parent)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        self.current_url = None
        self.error_log_path = None
        self.pipeline = None

        self._create_widgets()

    def _create_widgets(self):
        """创建界面组件"""
        # URL 输入区
        input_frame = tk.Frame(self)
        input_frame.grid(row=0, column=0, sticky='ew', padx=10, pady=10)
        input_frame.columnconfigure(1, weight=1)

        tk.Label(input_frame, text="URL:", font=('Arial', 11)).grid(
            row=0, column=0, padx=(0, 10)
        )

        self.url_entry = tk.Entry(input_frame, font=('Arial', 11))
        self.url_entry.grid(row=0, column=1, sticky='ew', padx=(0, 10))
        self.url_entry.bind('<Return>', lambda e: self.start_translation())

        self.translate_btn = tk.Button(
            input_frame,
            text="开始翻译",
            command=self.start_translation,
            bg='#1976d2',
            fg='white',
            font=('Arial', 11, 'bold'),
            padx=20,
            pady=5
        )
        self.translate_btn.grid(row=0, column=2)

        # 进度条
        self.progress_frame = ProgressFrame(self)
        self.progress_frame.grid(row=1, column=0, sticky='ew', padx=10, pady=(0, 10))

        # 错误提示区（默认隐藏）
        self.error_panel = ErrorPanel(self)
        self.error_panel.grid(row=2, column=0, sticky='ew', padx=10, pady=(0, 10))
        self.error_panel.hide()

        # 日志显示区
        log_frame = tk.LabelFrame(self, text="日志输出", font=('Arial', 10))
        log_frame.grid(row=3, column=0, sticky='nsew', padx=10, pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = LogTextWidget(
            log_frame,
            max_lines=LOG_MAX_LINES,
            font=('Monaco', 10),
            bg='#f5f5f5',
            wrap=tk.WORD
        )
        self.log_text.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)

    def start_translation(self):
        """开始翻译"""
        url = self.url_entry.get().strip()

        if not url:
            messagebox.showwarning("输入错误", "请输入文章 URL")
            return

        if not url.startswith('http'):
            messagebox.showwarning("输入错误", "URL 必须以 http:// 或 https:// 开头")
            return

        # 重置界面
        self.current_url = url
        self.error_log_path = None
        self.error_panel.hide()
        self.progress_frame.reset()
        self.log_text.clear()

        # 禁用输入
        self.url_entry.config(state=tk.DISABLED)
        self.translate_btn.config(state=tk.DISABLED)

        # 创建管线
        self.pipeline = TranslatePipeline(url, {
            'progress': self._on_progress,
            'log': self._on_log,
            'complete': self._on_complete,
            'error': self._on_error,
        })

        # 异步执行
        self.pipeline.run()

    def _on_progress(self, percent: int, message: str):
        """进度更新回调（线程安全）"""
        self.after(0, lambda: self.progress_frame.set_progress(percent, message))

    def _on_log(self, message: str):
        """日志输出回调（线程安全）"""
        self.after(0, lambda: self.log_text.append(message))

    def _on_complete(self, article_dir: Path):
        """完成回调（线程安全）"""
        def update_ui():
            self.url_entry.config(state=tk.NORMAL)
            self.translate_btn.config(state=tk.NORMAL)
            self.url_entry.delete(0, tk.END)

            # 显示成功消息
            result = messagebox.askyesno(
                "翻译完成",
                f"文章已保存到:\n{article_dir}\n\n是否在 Finder 中打开？"
            )

            if result:
                subprocess.run(['open', str(article_dir)])

        self.after(0, update_ui)

    def _on_error(self, error: Exception, log_path: Path):
        """错误回调（线程安全）"""
        def update_ui():
            self.error_log_path = log_path

            # 显示错误面板
            error_msg = f"翻译失败: {str(error)}\n详细日志已保存到: {log_path}"
            self.error_panel.show_error(
                error_msg,
                on_retry=self._retry_translation,
                on_export=self._export_error_log
            )
            self.error_panel.grid()

            # 恢复输入
            self.url_entry.config(state=tk.NORMAL)
            self.translate_btn.config(state=tk.NORMAL)

        self.after(0, update_ui)

    def _retry_translation(self):
        """重试翻译"""
        self.start_translation()

    def _export_error_log(self):
        """导出错误日志"""
        if self.error_log_path and self.error_log_path.exists():
            subprocess.run(['open', str(self.error_log_path)])
        else:
            messagebox.showwarning("错误", "日志文件不存在")
