from __future__ import annotations

from typing import Any

from internal_link_ai.related_mapper import map_internal_link_hints


def build_related_links(article_output: dict[str, Any]) -> list[dict[str, str]]:
    """article_output から関連記事リンク候補を生成する。"""
    links = map_internal_link_hints(article_output)
    # 最小実装として最大5件に制限。
    return links[:5]


class InternalLinkAI:
    """旧呼び出しとの互換性を維持する最小ラッパー。"""

    def generate_links(self, article: dict[str, Any]) -> dict[str, Any]:
        return {
            "article": str(article.get("title", "")).strip(),
            "article_id": str(article.get("article_id", "")).strip(),
            "related_links": build_related_links(article),
        }

    def process(self, article: dict[str, Any]) -> dict[str, Any]:
        return self.generate_links(article)
