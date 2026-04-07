from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from monitoring.log_helper import (
    log_batch_summary,
    log_failed_item,
    log_give_up,
    log_retry_enqueued,
)
from monitoring.slack_notifier import send_slack_block


def _event_id_line(item: dict[str, Any]) -> str:
    return f"event_id: {item.get('event_id', '')}"


def _reason_line(item: dict[str, Any], key: str = "reason") -> str:
    return f"reason: {item.get(key, '')}"


def report_failed_item(item: dict[str, Any]) -> None:
    """記事単位の失敗をログ/Slack通知する。"""
    log_failed_item(item)
    send_slack_block(
        "[FAILED] 記事投稿失敗",
        [
            f"slug: {item.get('slug', '')}",
            f"work_id: {item.get('work_id', '')}",
            f"keyword: {item.get('keyword', '')}",
            f"article_type: {item.get('article_type', '')}",
            f"error: {item.get('error_message', '')}",
            _reason_line(item),
            f"retryable: {item.get('retryable', '')}",
            f"retry_count: {item.get('retry_count', '')}",
            f"dry_run: {item.get('dry_run', '')}",
            _event_id_line(item),
        ],
    )


def report_batch_summary(summary: dict[str, Any]) -> None:
    """バッチ結果サマリーをログ/Slack通知する。"""
    enriched = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        **summary,
    }
    log_batch_summary(enriched)
    failed_slugs = enriched.get("failed_slugs", [])
    preview = failed_slugs[:5] if isinstance(failed_slugs, list) else []

    send_slack_block(
        "[BATCH] 実行結果サマリー",
        [
            f"success: {enriched.get('success_count', 0)}",
            f"skipped: {enriched.get('skipped_count', 0)}",
            f"failed: {enriched.get('failed_count', 0)}",
            "failed slugs:",
            *([f"- {slug}" for slug in preview] if preview else ["- なし"]),
            f"dry_run: {enriched.get('dry_run', '')}",
        ],
    )


def report_retry_enqueued(item: dict[str, Any]) -> None:
    """retry queue 追加をログ/Slack通知する。"""
    log_retry_enqueued(item)
    send_slack_block(
        "[RETRY QUEUED] 再試行キュー追加",
        [
            f"slug: {item.get('slug', '')}",
            f"reason: {item.get('reason', '')}",
            f"retry_count: {item.get('retry_count', 0)}",
            f"max_retry_count: {item.get('max_retry_count', 0)}",
            f"next_retry_at: {item.get('next_retry_at', '')}",
            _event_id_line(item),
        ],
    )


def report_give_up(item: dict[str, Any]) -> None:
    """give_up 到達をログ/Slack通知する。"""
    log_give_up(item)
    send_slack_block(
        "[GIVE UP] 再試行上限到達",
        [
            f"slug: {item.get('slug', '')}",
            f"keyword: {item.get('keyword', '')}",
            f"retry_count: {item.get('retry_count', '')}",
            f"last_error: {item.get('error_message', '')}",
            _reason_line(item),
            _event_id_line(item),
        ],
    )
