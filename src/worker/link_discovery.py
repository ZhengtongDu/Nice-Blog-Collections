"""Link discovery for directory/index pages."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

from translate import fetch_html, extract_metadata


_NAV_TAGS = {"nav", "header", "footer", "aside"}
_SKIP_PATHS = re.compile(
    r"^/(about|contact|tags|categories|author|page|search|login|signup|privacy|terms)(/|$)|^/$",
    re.IGNORECASE,
)
_SKIP_SCHEMES = {"javascript", "mailto", "tel", "data"}


def _normalize_url(url: str) -> str:
    """Strip trailing slash, fragment, and common tracking params."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    # Remove tracking query params
    if parsed.query:
        params = [
            p for p in parsed.query.split("&")
            if not re.match(r"^(utm_|ref=|source=)", p, re.IGNORECASE)
        ]
        query = "&".join(params)
    else:
        query = ""
    return urlunparse((parsed.scheme, parsed.netloc, path, "", query, ""))


def _is_same_domain(url: str, base_domain: str) -> bool:
    host = urlparse(url).netloc.lower()
    return host == base_domain or host.endswith("." + base_domain)


def _in_nav_element(tag) -> bool:
    for parent in tag.parents:
        if parent.name in _NAV_TAGS:
            return True
        cls = " ".join(parent.get("class", []))
        if re.search(r"\b(nav|menu|sidebar|footer|breadcrumb)\b", cls, re.IGNORECASE):
            return True
    return False


def _find_content_area(soup: BeautifulSoup):
    return (
        soup.find("article")
        or soup.find("main")
        or soup.find("div", class_=re.compile(r"content|prose", re.IGNORECASE))
        or soup.find("div", id="primary")
    )


def discover_links(url: str, store=None) -> dict[str, Any]:
    """Fetch a page and extract article-like links from it."""
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    # Page title
    og_title = soup.find("meta", property="og:title")
    if og_title:
        page_title = re.sub(r"\s*\|.*$", "", og_title.get("content", "")).strip()
    elif soup.title and soup.title.string:
        page_title = soup.title.string.strip()
    else:
        page_title = "Untitled"

    base_domain = urlparse(url).netloc.lower()
    content_area = _find_content_area(soup)

    # Collect all <a> tags
    all_anchors = soup.find_all("a", href=True)
    content_anchors = content_area.find_all("a", href=True) if content_area else []

    def _extract_links(anchors, skip_nav=True):
        seen = set()
        links = []
        for a in anchors:
            if skip_nav and _in_nav_element(a):
                continue
            raw_href = a["href"].strip()
            if not raw_href or raw_href.startswith("#"):
                continue
            abs_url = urljoin(url, raw_href)
            parsed = urlparse(abs_url)
            if parsed.scheme in _SKIP_SCHEMES:
                continue
            if not _is_same_domain(abs_url, base_domain):
                continue
            if _SKIP_PATHS.match(parsed.path):
                continue
            normalized = _normalize_url(abs_url)
            # Skip the page itself
            if _normalize_url(url) == normalized:
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            title = a.get_text(strip=True) or parsed.path.split("/")[-1].replace("-", " ").title()
            links.append({"url": normalized, "title": title})
        return links

    # Prefer content-area links if enough are found
    content_links = _extract_links(content_anchors) if content_anchors else []
    if len(content_links) >= 3:
        links = content_links
    else:
        links = _extract_links(all_anchors)

    # Mark already-translated articles
    if store:
        for link in links:
            matches = store.find_by_source_url(link["url"])
            link["alreadyExists"] = len(matches) > 0
    else:
        for link in links:
            link["alreadyExists"] = False

    return {
        "sourceURL": url,
        "pageTitle": page_title,
        "links": links,
    }
