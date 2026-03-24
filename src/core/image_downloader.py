"""图片下载模块

从 Markdown 中提取图片链接，下载到本地，并替换为相对路径。
"""

import re
import hashlib
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests

from config import USER_AGENT


def download_images(markdown: str, article_dir: Path, base_url: str) -> str:
    """
    下载 Markdown 中的图片到本地

    Args:
        markdown: 原始 Markdown 内容
        article_dir: 文章目录（如 articles/2026-03-23-slug/）
        base_url: 原文 URL（用于解析相对路径）

    Returns:
        替换后的 Markdown（图片链接改为本地路径）
    """
    images_dir = article_dir / "images"
    images_dir.mkdir(exist_ok=True)

    # 正则匹配 ![alt](url)
    pattern = r'!\[([^\]]*)\]\(([^)]+)\)'

    def replace_image(match):
        alt, url = match.groups()

        # 跳过 data: URL（内嵌图片）
        if url.startswith('data:'):
            return match.group(0)

        # 处理相对路径
        full_url = urljoin(base_url, url)

        try:
            # 下载图片
            filename = download_single_image(full_url, images_dir)
            # 返回本地路径
            return f'![{alt}](images/{filename})'
        except Exception as e:
            print(f"  [警告] 图片下载失败: {url} - {e}")
            # 保留原链接
            return match.group(0)

    return re.sub(pattern, replace_image, markdown)


def download_single_image(url: str, images_dir: Path) -> str:
    """
    下载单张图片

    Args:
        url: 图片 URL
        images_dir: 图片保存目录

    Returns:
        保存的文件名
    """
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(url, headers=headers, timeout=30, stream=True)
    resp.raise_for_status()

    # 从 URL 或 Content-Type 推断扩展名
    ext = get_image_extension(url, resp.headers.get('Content-Type', ''))

    # 使用 URL 的 hash 作为文件名（避免重复和特殊字符）
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    filename = f"{url_hash}{ext}"

    filepath = images_dir / filename

    # 如果已存在，跳过下载
    if filepath.exists():
        return filename

    # 保存图片
    with open(filepath, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    return filename


def get_image_extension(url: str, content_type: str) -> str:
    """
    推断图片扩展名

    Args:
        url: 图片 URL
        content_type: HTTP Content-Type 头

    Returns:
        扩展名（如 .jpg）
    """
    # 先从 URL 提取
    parsed = urlparse(url)
    path = parsed.path.lower()
    for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']:
        if path.endswith(ext):
            return ext

    # 从 Content-Type 推断
    content_type = content_type.lower()
    if 'jpeg' in content_type or 'jpg' in content_type:
        return '.jpg'
    elif 'png' in content_type:
        return '.png'
    elif 'gif' in content_type:
        return '.gif'
    elif 'webp' in content_type:
        return '.webp'
    elif 'svg' in content_type:
        return '.svg'

    # 默认 .jpg
    return '.jpg'
