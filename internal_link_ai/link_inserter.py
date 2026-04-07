from __future__ import annotations

import html
from typing import Any


def build_related_links_html(links: list[dict[str, str]]) -> str:
    """関連記事リンク配列からHTMLブロックを構築する。"""
    items: list[str] = []
    for link in links:
        title = html.escape(str(link.get("title", "関連記事")).strip() or "関連記事")
        url = html.escape(str(link.get("url", "")).strip())
        if not url:
            continue
        items.append(f'<li><a href="{url}">{title}</a></li>')

    if not items:
        return ""

    return (
        '<div class="related-links">'
        "<h2>関連記事</h2>"
        "<ul>"
        f"{''.join(items)}"
        "</ul>"
        "</div>"
    )


def insert_related_links(content_html: str, links: list[dict[str, str]]) -> str:
    """本文HTML末尾に関連記事ブロックを差し込む。"""
    base_html = (content_html or "").strip()
    related_html = build_related_links_html(links)
    if not related_html:
        return base_html

    if '<div class="related-links">' in base_html:
        return base_html

    return f"{base_html}{related_html}"


class LinkInserter:
    """旧呼び出し互換ラッパー。"""

    def insert(self, article: dict[str, Any], related_articles: list[dict[str, Any]], max_links: int = 5) -> dict[str, Any]:
        content = str(article.get("content", "")).strip()
        normalized = [
            {
                "title": str(item.get("title", "関連記事")).strip(),
                "url": str(item.get("url", item.get("link", "")).strip()),
            }
            for item in related_articles[:max_links]
        ]
        return {
            "title": str(article.get("title", "無題記事")).strip() or "無題記事",
            "content": insert_related_links(content, normalized),
        }
