"""审查发布 UI 界面"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.article_manager import ArticleManager


class ReviewTab(tk.Frame):
    """审查发布界面"""

    def __init__(self, parent):
        super().__init__(parent)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(1, weight=1)

        self.selected_article = None

        self._create_widgets()
        self.refresh_list()

    def _create_widgets(self):
        """创建界面组件"""
        # 左侧：文章列表
        left_frame = tk.Frame(self)
        left_frame.grid(row=0, column=0, rowspan=2, sticky='nsew', padx=(10, 5), pady=10)
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)

        # 列表标题和刷新按钮
        header_frame = tk.Frame(left_frame)
        header_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        header_frame.columnconfigure(0, weight=1)

        tk.Label(
            header_frame,
            text="待审查文章",
            font=('Arial', 12, 'bold')
        ).grid(row=0, column=0, sticky='w')

        tk.Button(
            header_frame,
            text="刷新",
            command=self.refresh_list,
            bg='#757575',
            fg='white',
            padx=10,
            pady=3
        ).grid(row=0, column=1, padx=(10, 0))

        # 文章列表（Treeview）
        list_frame = tk.Frame(left_frame)
        list_frame.grid(row=1, column=0, sticky='nsew')
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # 创建 Treeview
        columns = ('title', 'author', 'date')
        self.tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show='tree headings',
            selectmode='browse'
        )

        # 列标题
        self.tree.heading('#0', text='')
        self.tree.heading('title', text='标题')
        self.tree.heading('author', text='作者')
        self.tree.heading('date', text='添加日期')

        # 列宽
        self.tree.column('#0', width=0, stretch=False)
        self.tree.column('title', width=200)
        self.tree.column('author', width=100)
        self.tree.column('date', width=100)

        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')

        # 绑定选择事件
        self.tree.bind('<<TreeviewSelect>>', self._on_select)

        # 右侧：预览和操作
        right_frame = tk.Frame(self)
        right_frame.grid(row=0, column=1, rowspan=2, sticky='nsew', padx=(5, 10), pady=10)
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)

        # 操作按钮
        button_frame = tk.Frame(right_frame)
        button_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))

        tk.Button(
            button_frame,
            text="在 Finder 中打开",
            command=self._open_in_finder,
            bg='#1976d2',
            fg='white',
            padx=15,
            pady=5
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            button_frame,
            text="标记为已发布",
            command=self._mark_as_published,
            bg='#388e3c',
            fg='white',
            padx=15,
            pady=5
        ).pack(side=tk.LEFT)

        # 预览区
        preview_frame = tk.LabelFrame(right_frame, text="预览", font=('Arial', 10))
        preview_frame.grid(row=1, column=0, sticky='nsew')
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)

        self.preview_text = scrolledtext.ScrolledText(
            preview_frame,
            font=('Monaco', 10),
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.preview_text.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)

    def refresh_list(self):
        """刷新文章列表"""
        # 清空列表
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 加载 translated 状态的文章
        articles = ArticleManager.list_articles(status='translated')

        if not articles:
            self.tree.insert('', tk.END, values=('暂无待审查文章', '', ''))
            return

        # 填充列表
        for article in articles:
            self.tree.insert(
                '',
                tk.END,
                values=(
                    article.get('title', 'Untitled'),
                    article.get('author', 'Unknown'),
                    article.get('added', '')
                ),
                tags=(article['dir'],)  # 存储目录路径
            )

    def _on_select(self, event):
        """选择文章时的回调"""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        tags = self.tree.item(item, 'tags')

        if not tags:
            return

        article_dir = Path(tags[0])
        self.selected_article = article_dir

        # 加载预览
        try:
            content = ArticleManager.read_translated(article_dir)
            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete('1.0', tk.END)
            self.preview_text.insert('1.0', content)
            self.preview_text.config(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror("错误", f"加载预览失败: {e}")

    def _open_in_finder(self):
        """在 Finder 中打开文章目录"""
        if not self.selected_article:
            messagebox.showwarning("提示", "请先选择一篇文章")
            return

        subprocess.run(['open', str(self.selected_article)])

    def _mark_as_published(self):
        """标记为已发布"""
        if not self.selected_article:
            messagebox.showwarning("提示", "请先选择一篇文章")
            return

        result = messagebox.askyesno(
            "确认",
            "确定要将此文章标记为已发布吗？"
        )

        if result:
            try:
                ArticleManager.update_status(self.selected_article, 'published')
                messagebox.showinfo("成功", "已标记为已发布")
                self.refresh_list()
                self.selected_article = None
                self.preview_text.config(state=tk.NORMAL)
                self.preview_text.delete('1.0', tk.END)
                self.preview_text.config(state=tk.DISABLED)
            except Exception as e:
                messagebox.showerror("错误", f"更新状态失败: {e}")
