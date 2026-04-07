from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from article_generator.signal_template_router import detect_signal_mode


# 通常時のベース優先度
_BASE_PRIORITY: dict[str, int] = {
    "sale_article": 100,
    "latest_volume": 70,
    "volume_guide": 50,
    "summary": 40,
    "work_article": 30,
}

# 単独イベント優先度
_PRICE_CHANGED_PRIORITY: dict[str, int] = {
    "sale_article": 200,
}
_RELEASE_CHANGED_PRIORITY: dict[str, int] = {
    "latest_volume": 300,
    "volume_guide": 220,
    "summary": 180,
    "work_article": 160,
}

# 複合イベント優先度
_COMBINED_CHANGED_PRIORITY: dict[str, int] = {
    "sale_article": 260,
    "latest_volume": 320,
    "volume_guide": 240,
    "summary": 200,
    "work_article": 180,
}

_DEFAULT_PRIORITY = 10


@dataclass(frozen=True)
class CombinedSignalResult:
    """複合シグナル判定の戻り値。"""

    priority: int
    decision: str
    reason: str
    sub_reasons: list[str]
    signal_mode: str


def _normalize_article_type(article_type: str | None) -> str:
    return (article_type or "").strip()


def _normalize_reason(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    return text or fallback


def compute_final_priority(article_type: str, price_changed: bool, release_changed: bool) -> int:
    """article_type とイベント有無から最終 priority を計算する。"""
    normalized = _normalize_article_type(article_type)

    if price_changed and release_changed:
        return _COMBINED_CHANGED_PRIORITY.get(
            normalized,
            max(
                _BASE_PRIORITY.get(normalized, _DEFAULT_PRIORITY),
                _PRICE_CHANGED_PRIORITY.get(normalized, _DEFAULT_PRIORITY),
                _RELEASE_CHANGED_PRIORITY.get(normalized, _DEFAULT_PRIORITY),
            )
            + 20,
        )

    if release_changed:
        return _RELEASE_CHANGED_PRIORITY.get(normalized, _BASE_PRIORITY.get(normalized, _DEFAULT_PRIORITY))

    if price_changed:
        return _PRICE_CHANGED_PRIORITY.get(normalized, _BASE_PRIORITY.get(normalized, _DEFAULT_PRIORITY))

    return _BASE_PRIORITY.get(normalized, _DEFAULT_PRIORITY)


def compute_final_decision(
    article_type: str,
    price_changed: bool,
    release_changed: bool,
    policy_result: dict[str, Any] | None,
    *,
    dry_run: bool,
) -> str:
    """最終 decision を返す。policy_result がある場合は最優先で尊重する。"""
    if policy_result:
        existing_decision = str(policy_result.get("decision", "")).strip()
        if existing_decision:
            return existing_decision

    normalized_type = _normalize_article_type(article_type)

    if price_changed and release_changed:
        return "would_republish_combined_signal" if dry_run else "republish_allowed_combined_signal"

    if release_changed and normalized_type in {"latest_volume", "volume_guide", "summary", "work_article"}:
        return "would_republish_release_changed" if dry_run else "republish_allowed_release_changed"

    if price_changed and normalized_type == "sale_article":
        return "would_republish_price_changed" if dry_run else "republish_allowed_price_changed"

    return "would_skip_policy_blocked" if dry_run else "skip_policy_blocked"


def compute_final_reason(
    price_changed: bool,
    release_changed: bool,
    change_reason: str | None,
    release_change_reason: str | None,
) -> tuple[str, list[str]]:
    """最終 reason と sub_reasons を返す。"""
    normalized_price_reason = _normalize_reason(change_reason, "no_change")
    normalized_release_reason = _normalize_reason(release_change_reason, "no_change")

    sub_reasons: list[str] = []
    if price_changed and normalized_price_reason != "no_change":
        sub_reasons.append(normalized_price_reason)
    if release_changed and normalized_release_reason != "no_change":
        sub_reasons.append(normalized_release_reason)

    if price_changed and release_changed:
        return "combined_price_and_release_changed", sub_reasons
    if release_changed:
        return "release_changed_event", sub_reasons
    if price_changed:
        return "price_changed_event", sub_reasons

    return "no_signal", sub_reasons


def evaluate_combined_signal(
    article: dict[str, Any],
    policy_result: dict[str, Any] | None = None,
    *,
    dry_run: bool = True,
) -> CombinedSignalResult:
    """price/release シグナルを統合して最終 priority/decision/reason を返す。"""
    article_type = _normalize_article_type(str(article.get("article_type", "")))
    price_changed = bool(article.get("price_changed", False))
    release_changed = bool(article.get("release_changed", False))

    priority = compute_final_priority(article_type, price_changed, release_changed)

    reason, sub_reasons = compute_final_reason(
        price_changed=price_changed,
        release_changed=release_changed,
        change_reason=str(article.get("change_reason", "no_change")),
        release_change_reason=str(article.get("release_change_reason", "no_change")),
    )

    decision = compute_final_decision(
        article_type=article_type,
        price_changed=price_changed,
        release_changed=release_changed,
        policy_result=policy_result,
        dry_run=dry_run,
    )

    return CombinedSignalResult(
        priority=priority,
        decision=decision,
        reason=reason,
        sub_reasons=sub_reasons,
        signal_mode=detect_signal_mode(article),
    )


def build_combined_event(article: dict[str, Any]) -> dict[str, Any]:
    """通知用の統一イベント dict を返す。"""
    price_changed = bool(article.get("price_changed", False))
    release_changed = bool(article.get("release_changed", False))

    event_type = "none"
    if price_changed and release_changed:
        event_type = "combined"
    elif release_changed:
        event_type = "release_only"
    elif price_changed:
        event_type = "price_only"

    sub_reasons = article.get("sub_reasons", [])
    if not isinstance(sub_reasons, list):
        sub_reasons = []

    return {
        "event_type": event_type,
        "signal_mode": detect_signal_mode(article),
        "work_id": article.get("work_id", ""),
        "title": article.get("title", ""),
        "keyword": article.get("keyword", ""),
        "article_type": article.get("article_type", ""),
        "slug": article.get("slug", ""),
        "price_changed": price_changed,
        "previous_price": article.get("previous_price"),
        "current_price": article.get("current_price"),
        "price_diff": article.get("price_diff"),
        "discount_rate": article.get("discount_rate"),
        "change_reason": article.get("change_reason", "no_change"),
        "release_changed": release_changed,
        "previous_latest_volume_number": article.get("previous_latest_volume_number"),
        "current_latest_volume_number": article.get("current_latest_volume_number"),
        "release_change_reason": article.get("release_change_reason", "no_change"),
        "priority": article.get("priority", ""),
        "decision": article.get("decision", ""),
        "reason": article.get("reason", ""),
        "sub_reasons": sub_reasons,
        "dry_run": bool(article.get("dry_run", False)),
        "skipped": bool(article.get("skipped", False)),
        "success": bool(article.get("success", True)),
    }
