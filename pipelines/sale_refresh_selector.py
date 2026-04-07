from __future__ import annotations

from typing import Any

from pipelines.priority_policy import add_priority_to_item


def sort_items_by_priority(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """priority 降順で安定ソートした item 一覧を返す。"""
    with_index: list[tuple[int, dict[str, Any]]] = [
        (index, add_priority_to_item(item)) for index, item in enumerate(items)
    ]

    with_index.sort(key=lambda row: (-int(row[1].get("priority", 0)), row[0]))
    return [row[1] for row in with_index]


def filter_sale_articles(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """sale_article のみ抽出して返す。"""
    return [item for item in items if str(item.get("article_type", "")).strip() == "sale_article"]


def select_processing_items(items: list[dict[str, Any]], only_sale: bool = False) -> list[dict[str, Any]]:
    """sale only 設定を反映しつつ priority 順に処理対象を返す。"""
    targets = filter_sale_articles(items) if only_sale else list(items)
    return sort_items_by_priority(targets)
