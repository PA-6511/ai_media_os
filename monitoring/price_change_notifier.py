from __future__ import annotations

from typing import Any

from monitoring.slack_notifier import send_slack_block


def notify_price_change(event: dict[str, Any]) -> bool:
    """価格変動イベントを Slack 通知する。"""
    return send_slack_block(
        "[PRICE CHANGE] セール価格変動検知",
        [
            f"slug: {event.get('slug', '')}",
            f"work_id: {event.get('work_id', '')}",
            f"keyword: {event.get('keyword', '')}",
            f"article_type: {event.get('article_type', '')}",
            f"previous_price: {event.get('previous_price', '')}",
            f"current_price: {event.get('current_price', '')}",
            f"price_diff: {event.get('price_diff', '')}",
            f"discount_rate: {event.get('discount_rate', '')}",
            f"change_reason: {event.get('change_reason', '')}",
            f"price_changed: {event.get('price_changed', '')}",
            f"priority: {event.get('priority', '')}",
            f"decision: {event.get('decision', '')}",
            f"dry_run: {event.get('dry_run', '')}",
        ],
    )


def notify_price_change_batch_summary(summary: dict[str, Any]) -> bool:
    """価格変動バッチサマリーを Slack 通知する。"""
    return send_slack_block(
        "[PRICE CHANGE BATCH] 実行結果",
        [
            f"checked_count: {summary.get('checked_count', 0)}",
            f"changed_count: {summary.get('changed_count', 0)}",
            f"refresh_target_count: {summary.get('refresh_target_count', 0)}",
            f"skipped_count: {summary.get('skipped_count', 0)}",
            f"dry_run: {summary.get('dry_run', '')}",
        ],
    )
