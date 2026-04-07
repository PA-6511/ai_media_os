from __future__ import annotations

from typing import Final


SUPPORTED_TYPES: Final[set[str]] = {
    "volume_guide",
    "latest_volume",
    "summary",
    "sale_article",
    "work_article",
}


def normalize_article_type(article_type: str) -> str:
    """記事タイプを正規化し、未対応値は work_article にフォールバックする。"""
    normalized = (article_type or "").strip().lower()
    if normalized in SUPPORTED_TYPES:
        return normalized
    return "work_article"
