"""文章管理模块

扫描、读取、更新文章元数据。
"""

from pathlib import Path
from typing import Optional
import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ARTICLES_DIR = PROJECT_ROOT / "articles"


class ArticleManager:
    """文章管理器"""

    @staticmethod
    def list_articles(status: Optional[str] = None) -> list[dict]:
        """
        列出文章，可按状态筛选

        Args:
            status: 状态筛选（pending/translated/published），None 表示全部

        Returns:
            文章列表，每项包含元数据和目录路径
        """
        articles = []

        if not ARTICLES_DIR.exists():
            return articles

        for meta_path in ARTICLES_DIR.glob("*/metadata.yaml"):
            try:
                with open(meta_path, encoding="utf-8") as f:
                    meta = yaml.safe_load(f)

                # 添加目录路径
                meta['dir'] = str(meta_path.parent)

                # 状态筛选
                if status is None or meta.get('status') == status:
                    articles.append(meta)
            except Exception as e:
                print(f"[警告] 读取元数据失败: {meta_path} - {e}")
                continue

        # 按添加日期倒序排序
        articles.sort(key=lambda x: x.get('added', ''), reverse=True)
        return articles

    @staticmethod
    def update_status(article_dir: Path, new_status: str):
        """
        更新文章状态

        Args:
            article_dir: 文章目录路径
            new_status: 新状态（pending/translated/published）
        """
        meta_path = article_dir / "metadata.yaml"

        if not meta_path.exists():
            raise FileNotFoundError(f"元数据文件不存在: {meta_path}")

        with open(meta_path, encoding="utf-8") as f:
            meta = yaml.safe_load(f)

        meta['status'] = new_status

        with open(meta_path, 'w', encoding="utf-8") as f:
            yaml.dump(meta, f, allow_unicode=True, default_flow_style=False)

    @staticmethod
    def get_article(article_dir: Path) -> dict:
        """
        获取单篇文章的元数据

        Args:
            article_dir: 文章目录路径

        Returns:
            文章元数据
        """
        meta_path = article_dir / "metadata.yaml"

        if not meta_path.exists():
            raise FileNotFoundError(f"元数据文件不存在: {meta_path}")

        with open(meta_path, encoding="utf-8") as f:
            meta = yaml.safe_load(f)

        meta['dir'] = str(article_dir)
        return meta

    @staticmethod
    def read_translated(article_dir: Path) -> str:
        """
        读取翻译后的文章内容

        Args:
            article_dir: 文章目录路径

        Returns:
            翻译后的 Markdown 内容
        """
        translated_path = article_dir / "translated.md"

        if not translated_path.exists():
            raise FileNotFoundError(f"翻译文件不存在: {translated_path}")

        return translated_path.read_text(encoding="utf-8")
