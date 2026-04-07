from __future__ import annotations

from typing import Any

from internal_link_ai.article_search import build_link_candidate


def map_internal_link_hints(article_output: dict[str, Any]) -> list[dict[str, str]]:
    """article_output.internal_link_hints を関連記事候補に変換する。"""
    hints = article_output.get("internal_link_hints", [])
    if not isinstance(hints, list):
        return []

    mapped: list[dict[str, str]] = []
    seen: set[str] = set()

    for hint in hints:
        text = str(hint).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        mapped.append(build_link_candidate(text))

    return mapped


class RelatedMapper:
    """旧インターフェース互換の薄いラッパー。"""

    def map_same_work(self, work_id: str, article_db: list[dict[str, Any]], limit: int = 6) -> dict[str, list[dict[str, str]]]:
        _ = work_id
        _ = limit
        result: dict[str, list[dict[str, str]]] = {}
        for row in article_db:
            article_id = str(row.get("article_id", "")).strip()
            if not article_id:
                continue
            result[article_id] = map_internal_link_hints(row)
        return result
