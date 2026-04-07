from __future__ import annotations

from typing import Any


def build_release_refresh_targets(item: dict[str, Any], release_event: dict[str, Any]) -> dict[str, Any]:
    """新刊イベントから再生成対象タイプと理由を返す。"""
    article_type = str(item.get("article_type", "")).strip()
    release_changed = bool(release_event.get("release_changed", False))

    if not release_changed:
        return {
            "release_target": False,
            "target_reason": "release_not_changed",
            "target_article_types": [],
        }

    target_article_types = ["latest_volume", "volume_guide", "summary"]
    if str(release_event.get("current_availability_status", "")).strip().lower() == "available":
        target_article_types.append("work_article")

    release_target = article_type in set(target_article_types)
    if release_target:
        return {
            "release_target": True,
            "target_reason": "release_changed_target_article_type",
            "target_article_types": target_article_types,
        }

    return {
        "release_target": False,
        "target_reason": "release_changed_but_not_target_article_type",
        "target_article_types": target_article_types,
    }
