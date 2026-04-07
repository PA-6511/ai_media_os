from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from monitoring.log_helper import log_price_change_batch_summary, log_price_change_event
from monitoring.price_change_notifier import notify_price_change, notify_price_change_batch_summary


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _threshold_price_diff_yen() -> float:
    return _to_float(os.getenv("PRICE_NOTIFY_MIN_DIFF_YEN", "50"), default=50.0)


def _threshold_discount_rate_up() -> float:
    return _to_float(os.getenv("PRICE_NOTIFY_MIN_DISCOUNT_RATE_UP", "5"), default=5.0)


def is_notifiable_change(event: dict[str, Any]) -> bool:
    """通知対象の価格変動か判定する。"""
    if not bool(event.get("price_changed", False)):
        return False

    article_type = str(event.get("article_type", "")).strip()
    if article_type != "sale_article":
        return False

    price_diff = _to_float(event.get("price_diff"), default=0.0)
    discount_rate_diff = _to_float(event.get("discount_rate_diff"), default=0.0)
    change_reason = str(event.get("change_reason", "")).strip()

    # 最小版要件: どれか1つ満たせば通知対象
    if price_diff <= -_threshold_price_diff_yen():
        return True
    if discount_rate_diff >= _threshold_discount_rate_up():
        return True
    if "discount_rate_threshold" in change_reason:
        return True
    return bool(event.get("price_changed", False))


def report_price_change(event: dict[str, Any]) -> None:
    """価格変動イベントをログし、必要時に Slack 通知する。"""
    payload = {
        "checked_at": event.get("checked_at", datetime.now(timezone.utc).isoformat()),
        **event,
    }
    log_price_change_event(payload)

    if is_notifiable_change(payload):
        notify_price_change(payload)


def report_price_change_batch_summary(summary: dict[str, Any]) -> None:
    """価格変動バッチサマリーをログし、必要時に Slack 通知する。"""
    payload = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        **summary,
    }
    log_price_change_batch_summary(payload)

    if int(payload.get("changed_count", 0) or 0) > 0:
        notify_price_change_batch_summary(payload)
