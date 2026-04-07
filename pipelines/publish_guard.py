from __future__ import annotations

from typing import Any

from pipelines.publish_history import find_by_slug
from pipelines.post_status_store import get_status_by_slug
from pipelines.republish_policy import evaluate_policy
from wordpress_publisher.wp_client import WordPressClient


def check_local_history(slug: str) -> dict[str, Any] | None:
    """ローカル履歴DBで slug の既存投稿を確認する。"""
    status_record = get_status_by_slug(slug)
    history_record = find_by_slug(slug)

    if not status_record and not history_record:
        return None

    merged: dict[str, Any] = {}
    if history_record:
        merged.update(history_record)
    if status_record:
        merged.update(status_record)

    # post_status_tracking のみ存在するケースでは published_at が欠けるため補完する。
    if "published_at" not in merged:
        merged["published_at"] = merged.get("updated_at", "")

    merged["source"] = "local"
    return merged


def check_wordpress_existing(slug: str, client: WordPressClient) -> dict[str, Any] | None:
    """WordPress 側で slug の既存投稿を確認する。"""
    return client.find_post_by_slug(slug)


def evaluate_publish_decision(article: dict[str, Any], client: WordPressClient) -> dict[str, Any]:
    """重複チェックと再投稿ポリシーを統合して最終判定する。"""
    normalized_slug = str(article.get("slug", "")).strip()
    if not normalized_slug:
        raise ValueError("slug が空です")

    local_hit = check_local_history(normalized_slug)
    if local_hit:
        policy = evaluate_policy(article, local_hit)
        return {
            **policy,
            "source": "local",
            "existing_post_id": local_hit.get("post_id"),
            "existing_link": local_hit.get("link", ""),
            "slug": normalized_slug,
        }

    wp_hit = check_wordpress_existing(normalized_slug, client)
    if wp_hit:
        policy = evaluate_policy(article, wp_hit)
        return {
            **policy,
            "source": "wordpress",
            "existing_post_id": wp_hit.get("id"),
            "existing_link": wp_hit.get("link", ""),
            "slug": normalized_slug,
        }

    return {
        "decision": "publish_new",
        "reason": "not_found",
        "source": "none",
        "slug": normalized_slug,
    }


def should_publish(article: dict[str, Any], client: WordPressClient) -> dict[str, Any]:
    """投稿可否を判定して結果を返す。"""
    decision_result = evaluate_publish_decision(article, client)
    decision = decision_result.get("decision", "skip_policy_blocked")
    allow_publish = decision in {
        "publish_new",
        "republish_allowed",
        "retry_failed",
        "republish_allowed_price_changed",
        "republish_allowed_release_changed",
        "republish_allowed_combined_signal",
    }

    return {
        **decision_result,
        "should_publish": allow_publish,
    }
