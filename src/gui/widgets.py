"""通用 GUI 组件

提供可复用的 UI 组件。
"""

import tkinter as tk
from tkinter import scrolledtext, ttk
from pathlib import Path


class LogTextWidget(scrolledtext.ScrolledText):
    """带自动滚动的日志文本框"""

    def __init__(self, parent, max_lines=1000, **kwargs):
        """
        初始化日志文本框

        Args:
            parent: 父容器
            max_lines: 最大行数
            **kwargs: 传递给 ScrolledText 的其他参数
        """
        super().__init__(parent, **kwargs)
        self.max_lines = max_lines
        self.config(state=tk.DISABLED)  # 只读

    def append(self, text: str):
        """
        追加日志文本

        Args:
            text: 要追加的文本
        """
        self.config(state=tk.NORMAL)
        self.insert(tk.END, text + "\n")

        # 限制行数
        line_count = int(self.index('end-1c').split('.')[0])
        if line_count > self.max_lines:
            self.delete('1.0', f'{line_count - self.max_lines}.0')

        self.see(tk.END)  # 自动滚动到底部
        self.config(state=tk.DISABLED)

    def clear(self):
        """清空日志"""
        self.config(state=tk.NORMAL)
        self.delete('1.0', tk.END)
        self.config(state=tk.DISABLED)


class ErrorPanel(tk.Frame):
    """错误提示面板"""

    def __init__(self, parent, **kwargs):
        """
        初始化错误面板

        Args:
            parent: 父容器
            **kwargs: 传递给 Frame 的其他参数
        """
        super().__init__(parent, bg='#ffebee', **kwargs)
        self.columnconfigure(0, weight=1)

        # 错误图标和消息
        self.error_label = tk.Label(
            self,
            text="",
            bg='#ffebee',
            fg='#c62828',
            font=('Arial', 11),
            wraplength=700,
            justify=tk.LEFT
        )
        self.error_label.grid(row=0, column=0, sticky='ew', padx=10, pady=10)

        # 按钮容器
        self.button_frame = tk.Frame(self, bg='#ffebee')
        self.button_frame.grid(row=1, column=0, sticky='ew', padx=10, pady=(0, 10))

        self.retry_btn = None
        self.export_btn = None

    def show_error(self, message: str, on_retry=None, on_export=None):
        """
        显示错误信息

        Args:
            message: 错误消息
            on_retry: 重试回调函数
            on_export: 导出日志回调函数
        """
        self.error_label.config(text=f"⚠️ {message}")

        # 清除旧按钮
        for widget in self.button_frame.winfo_children():
            widget.destroy()

        # 添加重试按钮
        if on_retry:
            self.retry_btn = tk.Button(
                self.button_frame,
                text="重试",
                command=on_retry,
                bg='#1976d2',
                fg='white',
                padx=15,
                pady=5
            )
            self.retry_btn.pack(side=tk.LEFT, padx=5)

        # 添加导出按钮
        if on_export:
            self.export_btn = tk.Button(
                self.button_frame,
                text="导出错误日志",
                command=on_export,
                bg='#757575',
                fg='white',
                padx=15,
                pady=5
            )
            self.export_btn.pack(side=tk.LEFT, padx=5)

    def hide(self):
        """隐藏错误面板"""
        self.grid_remove()


class ProgressFrame(tk.Frame):
    """进度条组件"""

    def __init__(self, parent, **kwargs):
        """
        初始化进度条

        Args:
            parent: 父容器
            **kwargs: 传递给 Frame 的其他参数
        """
        super().__init__(parent, **kwargs)
        self.columnconfigure(0, weight=1)

        # 进度条
        self.progressbar = ttk.Progressbar(
            self,
            mode='determinate',
            maximum=100
        )
        self.progressbar.grid(row=0, column=0, sticky='ew', pady=(0, 5))

        # 百分比标签
        self.label = tk.Label(
            self,
            text="0%",
            font=('Arial', 9),
            fg='#666'
        )
        self.label.grid(row=1, column=0)

    def set_progress(self, percent: int, message: str = ""):
        """
        更新进度

        Args:
            percent: 进度百分比（0-100）
            message: 进度消息
        """
        self.progressbar['value'] = percent
        text = f"{percent}%"
        if message:
            text += f" - {message}"
        self.label.config(text=text)

    def reset(self):
        """重置进度"""
        self.progressbar['value'] = 0
        self.label.config(text="0%")
