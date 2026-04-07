from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from pipelines.combined_signal_policy import compute_final_reason


# article_type ごとの再投稿TTL（時間）
_DEFAULT_REPUBLISH_RULES_HOURS: dict[str, float] = {
    "volume_guide": 30 * 24,
    "latest_volume": 7 * 24,
    "summary": 30 * 24,
    "sale_article": 6,
    "work_article": 60 * 24,
}


def _load_sale_ttl_hours() -> float:
    """sale_article のTTL（時間）を環境変数から読み込む。"""
    raw = (os.getenv("SALE_ARTICLE_TTL_HOURS", "6") or "").strip()
    try:
        parsed = float(raw)
    except ValueError:
        parsed = 6.0

    # 0 以下は不正値として安全側デフォルトを使う。
    if parsed <= 0:
        return 6.0
    return parsed


def get_republish_rules() -> dict[str, float]:
    """再投稿TTLルール（時間）を返す。"""
    rules = dict(_DEFAULT_REPUBLISH_RULES_HOURS)
    rules["sale_article"] = _load_sale_ttl_hours()
    return rules


def _parse_datetime(value: str | None) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None

    # WordPress の `...Z` 形式にも対応する。
    normalized = text.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def should_republish(
    article_type: str,
    previous_status: str,
    updated_at: str | None,
    now: datetime,
) -> tuple[bool, str, str]:
    """記事タイプ・前回状態・更新時刻から再投稿可否を返す。"""
    normalized_status = (previous_status or "").strip().lower()
    normalized_type = (article_type or "").strip()

    if normalized_status == "failed":
        return True, "retry_failed", "previous_failed"

    ttl_hours = get_republish_rules().get(normalized_type)
    if ttl_hours is None:
        # 未知 article_type は保守的に再投稿禁止。
        return False, "skip_already_published", "unknown_article_type"

    updated_dt = _parse_datetime(updated_at)
    if updated_dt is None:
        return False, "skip_already_published", f"{normalized_type}_missing_updated_at"

    elapsed_seconds = max(0.0, (now - updated_dt).total_seconds())
    ttl_seconds = float(ttl_hours * 60 * 60)
    if elapsed_seconds >= ttl_seconds:
        return True, "republish_allowed", f"{normalized_type}_ttl_expired_{int(ttl_hours)}h"

    return False, "skip_policy_blocked", f"{normalized_type}_not_due_{int(ttl_hours)}h"


def evaluate_policy(
    article: dict[str, Any],
    existing_record: dict[str, Any] | None,
    price_change_event: dict[str, Any] | None = None,
    release_change_event: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """既存レコードを含めて最終ポリシー判定を行う。"""
    if not existing_record:
        return {
            "decision": "publish_new",
            "reason": "not_found",
        }

    article_type = str(article.get("article_type", "")).strip()
    price_changed = bool(article.get("price_changed", False)) or bool(
        (price_change_event or {}).get("price_changed", False)
    )
    release_changed = bool(article.get("release_changed", False)) or bool(
        (release_change_event or {}).get("release_changed", False)
    )
    change_reason = str(article.get("change_reason", "no_change")).strip()
    release_change_reason = str(article.get("release_change_reason", "no_change")).strip()

    signal_reason, sub_reasons = compute_final_reason(
        price_changed=price_changed,
        release_changed=release_changed,
        change_reason=change_reason,
        release_change_reason=release_change_reason,
    )

    if price_changed and release_changed:
        return {
            "decision": "republish_allowed_combined_signal",
            "reason": signal_reason,
            "sub_reasons": sub_reasons,
        }

    if article_type in {"latest_volume", "volume_guide", "summary", "work_article"} and release_changed:
        return {
            "decision": "republish_allowed_release_changed",
            "reason": signal_reason,
            "sub_reasons": sub_reasons,
        }

    if article_type == "sale_article" and price_changed:
        return {
            "decision": "republish_allowed_price_changed",
            "reason": signal_reason,
            "sub_reasons": sub_reasons,
        }

    previous_status = str(existing_record.get("status", "")).strip().lower()

    # updated_at -> published_at -> modified_gmt の順で利用する。
    updated_at = (
        str(existing_record.get("updated_at", "")).strip()
        or str(existing_record.get("published_at", "")).strip()
        or str(existing_record.get("modified_gmt", "")).strip()
    )

    now = datetime.now(timezone.utc)
    allowed, decision, reason = should_republish(
        article_type=article_type,
        previous_status=previous_status,
        updated_at=updated_at,
        now=now,
    )

    if allowed:
        return {
            "decision": decision,
            "reason": reason,
        }

    return {
        "decision": decision,
        "reason": reason,
    }
