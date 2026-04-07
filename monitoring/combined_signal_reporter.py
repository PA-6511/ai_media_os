from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from monitoring.combined_signal_notifier import notify_combined_signal, notify_combined_signal_batch_summary
from monitoring.journey_signal_adapter import (
    build_journey_signal_payload,
    merge_journey_into_event,
)
from monitoring.log_helper import log_combined_signal_batch_summary, log_combined_signal_event
from monitoring.price_change_reporter import is_notifiable_change
from monitoring.release_change_reporter import is_notifiable_release_change


def classify_event_type(event: dict[str, Any]) -> str:
    """price/release の組み合わせから event_type を返す。"""
    price_changed = bool(event.get("price_changed", False))
    release_changed = bool(event.get("release_changed", False))

    if price_changed and release_changed:
        return "combined"
    if release_changed:
        return "release_only"
    if price_changed:
        return "price_only"
    return "none"


def is_notifiable_combined_signal(event: dict[str, Any]) -> bool:
    """統合通知の送信可否を判定する。"""
    event_type = str(event.get("event_type", classify_event_type(event))).strip()

    if event_type == "combined":
        # 最小要件: combined は常に通知する。
        return True
    if event_type == "release_only":
        return is_notifiable_release_change(event)
    if event_type == "price_only":
        return is_notifiable_change(event)
    return False


def normalize_combined_event(event: dict[str, Any]) -> dict[str, Any]:
    """統合通知の共通イベント形式へ正規化する。"""
    event_type = classify_event_type(event)
    checked_at = str(event.get("checked_at", "")).strip() or datetime.now(timezone.utc).isoformat()

    sub_reasons = event.get("sub_reasons", [])
    if not isinstance(sub_reasons, list):
        sub_reasons = []

    payload = {
        "checked_at": checked_at,
        "event_type": event_type,
        "work_id": event.get("work_id", ""),
        "title": event.get("title", ""),
        "keyword": event.get("keyword", ""),
        "article_type": event.get("article_type", ""),
        "slug": event.get("slug", ""),
        "price_changed": bool(event.get("price_changed", False)),
        "previous_price": event.get("previous_price"),
        "current_price": event.get("current_price"),
        "price_diff": event.get("price_diff"),
        "discount_rate": event.get("discount_rate"),
        "change_reason": event.get("change_reason", "no_change"),
        "release_changed": bool(event.get("release_changed", False)),
        "previous_latest_volume_number": event.get("previous_latest_volume_number"),
        "current_latest_volume_number": event.get("current_latest_volume_number"),
        "release_change_reason": event.get("release_change_reason", "no_change"),
        "priority": event.get("priority", ""),
        "decision": event.get("decision", ""),
        "reason": event.get("reason", ""),
        "sub_reasons": sub_reasons,
        "dry_run": bool(event.get("dry_run", False)),
        "skipped": bool(event.get("skipped", False)),
        "success": bool(event.get("success", True)),
    }

    # Buyer Journey 情報を通知イベントへ付与
    journey_payload = build_journey_signal_payload(event)
    return merge_journey_into_event(payload, journey_payload)


def report_combined_signal(event: dict[str, Any]) -> None:
    """統合イベントをログ出力し、条件を満たす場合に通知する。"""
    payload = normalize_combined_event(event)
    if payload.get("event_type") == "none":
        return

    log_combined_signal_event(payload)
    if is_notifiable_combined_signal(payload):
        notify_combined_signal(payload)


def build_combined_signal_batch_summary(
    events: list[dict[str, Any]],
    *,
    dry_run: bool,
    failed_count: int = 0,
) -> dict[str, Any]:
    """統合イベント配列からバッチサマリーを作る。"""
    normalized = [normalize_combined_event(row) for row in events]
    checked_rows = [row for row in normalized if str(row.get("event_type", "")) in {"combined", "price_only", "release_only"}]

    combined_count = sum(1 for row in checked_rows if row.get("event_type") == "combined")
    price_only_count = sum(1 for row in checked_rows if row.get("event_type") == "price_only")
    release_only_count = sum(1 for row in checked_rows if row.get("event_type") == "release_only")

    refresh_decisions = {
        "republish_allowed_price_changed",
        "republish_allowed_release_changed",
        "republish_allowed_combined_signal",
        "would_republish_price_changed",
        "would_republish_release_changed",
        "would_republish_combined_signal",
        "republish_allowed",
        "would_republish",
        "publish_new",
        "would_publish_new",
        "retry_failed",
        "would_retry_failed",
    }
    refresh_target_count = sum(
        1
        for row in checked_rows
        if str(row.get("decision", "")).strip() in refresh_decisions
    )

    skipped_count = sum(
        1
        for row in checked_rows
        if bool(row.get("skipped", False))
        or str(row.get("decision", "")).startswith("skip")
        or str(row.get("decision", "")).startswith("would_skip")
    )

    return {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "checked_count": len(checked_rows),
        "combined_count": combined_count,
        "price_only_count": price_only_count,
        "release_only_count": release_only_count,
        "refresh_target_count": refresh_target_count,
        "skipped_count": skipped_count,
        "failed_count": int(failed_count),
        "dry_run": bool(dry_run),
    }


def report_combined_signal_batch_summary(summary: dict[str, Any]) -> None:
    """統合バッチサマリーをログ出力し、必要時に通知する。"""
    payload = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        **summary,
    }
    log_combined_signal_batch_summary(payload)

    always_notify = (os.getenv("COMBINED_BATCH_NOTIFY_ALWAYS", "1") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    has_signal = int(payload.get("combined_count", 0) or 0) > 0 or int(payload.get("price_only_count", 0) or 0) > 0 or int(payload.get("release_only_count", 0) or 0) > 0

    if always_notify or has_signal:
        notify_combined_signal_batch_summary(payload)
