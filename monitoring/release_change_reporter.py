from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from monitoring.log_helper import log_release_change_batch_summary, log_release_change_event
from monitoring.release_change_notifier import notify_release_batch_summary, notify_release_change
from release_calendar_ai.release_change_detector import is_significant_release_change


_TARGET_ARTICLE_TYPES = {"latest_volume", "volume_guide", "summary"}


def is_notifiable_release_change(event: dict[str, Any]) -> bool:
    """通知対象の新刊イベントか判定する。"""
    if not bool(event.get("release_changed", False)):
        return False

    reason = str(event.get("release_change_reason", "")).strip()
    if reason == "no_change":
        return False

    article_type = str(event.get("article_type", "")).strip()
    if article_type not in _TARGET_ARTICLE_TYPES:
        return False

    return is_significant_release_change(event)


def report_release_change(event: dict[str, Any]) -> None:
    """新刊イベントをログし、必要時に Slack 通知する。"""
    payload = {
        "checked_at": event.get("checked_at", datetime.now(timezone.utc).isoformat()),
        **event,
    }
    log_release_change_event(payload)

    if is_notifiable_release_change(payload):
        notify_release_change(payload)


def report_release_batch_summary(summary: dict[str, Any]) -> None:
    """新刊イベントサマリーをログし、必要時に Slack 通知する。"""
    payload = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        **summary,
    }
    log_release_change_batch_summary(payload)

    if int(payload.get("release_changed_count", 0) or 0) > 0:
        notify_release_batch_summary(payload)
