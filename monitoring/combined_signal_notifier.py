from __future__ import annotations

from typing import Any

from monitoring.slack_notifier import send_slack_block


def build_combined_signal_title(event: dict[str, Any]) -> str:
    """event_type に応じて Slack タイトルを作る。"""
    event_type = str(event.get("event_type", "")).strip()
    if event_type == "combined":
        return "[COMBINED SIGNAL] 価格変動 + 新刊イベント検知"
    if event_type == "release_only":
        return "[RELEASE SIGNAL] 新刊イベント検知"
    return "[PRICE SIGNAL] 価格変動検知"


def build_combined_signal_lines(event: dict[str, Any]) -> list[str]:
    """通知本文の行配列を作る。"""
    sub_reasons = event.get("sub_reasons", [])
    if isinstance(sub_reasons, list):
        sub_reason_text = ",".join(str(x) for x in sub_reasons)
    else:
        sub_reason_text = str(sub_reasons or "")

    next_summary = event.get("next_articles_summary", [])
    if isinstance(next_summary, list):
        next_summary_text = " / ".join(str(x) for x in next_summary if str(x).strip())
    else:
        next_summary_text = str(next_summary or "")

    return [
        f"event_type: {event.get('event_type', '')}",
        f"slug: {event.get('slug', '')}",
        f"work_id: {event.get('work_id', '')}",
        f"title: {event.get('title', '')}",
        f"keyword: {event.get('keyword', '')}",
        f"article_type: {event.get('article_type', '')}",
        f"price_changed: {event.get('price_changed', False)}",
        f"previous_price: {event.get('previous_price', '')}",
        f"current_price: {event.get('current_price', '')}",
        f"price_diff: {event.get('price_diff', '')}",
        f"discount_rate: {event.get('discount_rate', '')}",
        f"change_reason: {event.get('change_reason', '')}",
        f"release_changed: {event.get('release_changed', False)}",
        f"previous_latest_volume_number: {event.get('previous_latest_volume_number', '')}",
        f"current_latest_volume_number: {event.get('current_latest_volume_number', '')}",
        f"release_change_reason: {event.get('release_change_reason', '')}",
        f"priority: {event.get('priority', '')}",
        f"decision: {event.get('decision', '')}",
        f"reason: {event.get('reason', '')}",
        f"sub_reasons: {sub_reason_text}",
        f"stage: {event.get('stage', '')}",
        f"journey_mode: {event.get('journey_mode', '')}",
        f"is_release_optimized: {event.get('is_release_optimized', False)}",
        f"is_sale_optimized: {event.get('is_sale_optimized', False)}",
        f"cta: {event.get('cta_text', '')}",
        f"next: {next_summary_text}",
        f"dry_run: {event.get('dry_run', '')}",
    ]


def notify_combined_signal(event: dict[str, Any]) -> bool:
    """複合シグナルを Slack 通知する。"""
    title = build_combined_signal_title(event)
    lines = build_combined_signal_lines(event)
    return send_slack_block(title, lines)


def notify_combined_signal_batch_summary(summary: dict[str, Any]) -> bool:
    """複合シグナルのバッチサマリーを Slack 通知する。"""
    return send_slack_block(
        "[COMBINED SIGNAL BATCH]",
        [
            f"checked_count: {summary.get('checked_count', 0)}",
            f"combined_count: {summary.get('combined_count', 0)}",
            f"price_only_count: {summary.get('price_only_count', 0)}",
            f"release_only_count: {summary.get('release_only_count', 0)}",
            f"refresh_target_count: {summary.get('refresh_target_count', 0)}",
            f"skipped_count: {summary.get('skipped_count', 0)}",
            f"failed_count: {summary.get('failed_count', 0)}",
            f"dry_run: {summary.get('dry_run', '')}",
        ],
    )
