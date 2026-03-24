"""主窗口应用程序"""

import tkinter as tk
from tkinter import ttk
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from gui.translate_tab import TranslateTab
from gui.review_tab import ReviewTab
from config import WINDOW_WIDTH, WINDOW_HEIGHT


class BlogTranslatorApp(tk.Tk):
    """博文翻译助手主窗口"""

    def __init__(self):
        super().__init__()

        self.title("博文翻译助手")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

        # 设置最小窗口大小
        self.minsize(800, 600)

        self._create_widgets()
        self._create_menu()

    def _create_widgets(self):
        """创建界面组件"""
        # 创建 Notebook（Tab 容器）
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 翻译 Tab
        self.translate_tab = TranslateTab(self.notebook)
        self.notebook.add(self.translate_tab, text="翻译")

        # 审查 Tab
        self.review_tab = ReviewTab(self.notebook)
        self.notebook.add(self.review_tab, text="审查发布")

        # 状态栏
        self.status_bar = tk.Label(
            self,
            text="就绪",
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            font=('Arial', 9)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="退出", command=self.quit)

        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self._show_about)

    def _show_about(self):
        """显示关于对话框"""
        about_window = tk.Toplevel(self)
        about_window.title("关于")
        about_window.geometry("400x200")
        about_window.resizable(False, False)

        tk.Label(
            about_window,
            text="博文翻译助手",
            font=('Arial', 16, 'bold')
        ).pack(pady=(20, 10))

        tk.Label(
            about_window,
            text="版本 1.0.0",
            font=('Arial', 10)
        ).pack()

        tk.Label(
            about_window,
            text="\n自动化翻译英文技术博客为微信公众号文章",
            font=('Arial', 10),
            wraplength=350
        ).pack(pady=10)

        tk.Button(
            about_window,
            text="确定",
            command=about_window.destroy,
            padx=20,
            pady=5
        ).pack(pady=10)


def main():
    """主函数"""
    app = BlogTranslatorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
