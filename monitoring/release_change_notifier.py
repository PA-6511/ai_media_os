from __future__ import annotations

from typing import Any

from monitoring.slack_notifier import send_slack_block


def notify_release_change(event: dict[str, Any]) -> bool:
    """新刊イベントを Slack 通知する。"""
    return send_slack_block(
        "[RELEASE CHANGE] 新刊イベント検知",
        [
            f"slug: {event.get('slug', '')}",
            f"work_id: {event.get('work_id', '')}",
            f"title: {event.get('title', '')}",
            f"keyword: {event.get('keyword', '')}",
            f"article_type: {event.get('article_type', '')}",
            f"previous_latest_volume_number: {event.get('previous_latest_volume_number', '')}",
            f"current_latest_volume_number: {event.get('current_latest_volume_number', '')}",
            f"previous_latest_release_date: {event.get('previous_latest_release_date', '')}",
            f"current_latest_release_date: {event.get('current_latest_release_date', '')}",
            f"availability_status: {event.get('current_availability_status', event.get('availability_status', ''))}",
            f"release_change_reason: {event.get('release_change_reason', '')}",
            f"release_changed: {event.get('release_changed', '')}",
            f"priority: {event.get('priority', '')}",
            f"decision: {event.get('decision', '')}",
            f"dry_run: {event.get('dry_run', '')}",
        ],
    )


def notify_release_batch_summary(summary: dict[str, Any]) -> bool:
    """新刊イベントバッチサマリーを Slack 通知する。"""
    return send_slack_block(
        "[RELEASE BATCH] 実行結果",
        [
            f"checked_count: {summary.get('checked_count', 0)}",
            f"release_changed_count: {summary.get('release_changed_count', 0)}",
            f"refresh_target_count: {summary.get('refresh_target_count', 0)}",
            f"skipped_count: {summary.get('skipped_count', 0)}",
            f"dry_run: {summary.get('dry_run', '')}",
        ],
    )
