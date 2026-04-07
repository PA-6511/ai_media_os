from __future__ import annotations

from typing import Any

from pipelines.combined_signal_policy import compute_final_priority


def get_article_priority(
    article_type: str,
    price_changed: bool = False,
    release_changed: bool = False,
) -> int:
    """article_type とイベント有無から優先度を返す。"""
    return compute_final_priority(
        article_type=(article_type or "").strip(),
        price_changed=price_changed,
        release_changed=release_changed,
    )


def add_priority_to_item(item: dict[str, Any]) -> dict[str, Any]:
    """item に priority を付与した新しい dict を返す。"""
    existing_priority = item.get("priority")
    if isinstance(existing_priority, int):
        return {
            **item,
            "priority": existing_priority,
        }

    article_type = str(item.get("article_type", "")).strip()
    price_changed = bool(item.get("price_changed", False))
    release_changed = bool(item.get("release_changed", False))
    priority = get_article_priority(
        article_type,
        price_changed=price_changed,
        release_changed=release_changed,
    )
    return {
        **item,
        "priority": priority,
    }
