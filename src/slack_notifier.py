"""src/slack_notifier.py

sale_end_check 向け Slack 通知ヘルパー。
実際の送信は monitoring.slack_notifier に委譲する。
"""
from __future__ import annotations

from typing import Any


def notify_sale_ended(ended_items: list[dict[str, Any]], dry_run: bool = False) -> bool:
    """セール終了アイテムを Slack へ通知する。

    Args:
        ended_items: check_sale_end の result["ended"] に相当する list。
                     各要素は {"work_id": str, "old_status": str, "new_status": str,
                               "sale_end_date": str, ...} を含む。
        dry_run:     True の場合は送信せず False を返す。

    Returns:
        bool: 送信成功なら True
    """
    if dry_run:
        return False

    try:
        from monitoring.slack_notifier import send_slack_block  # type: ignore[import]
    except ImportError:
        return False

    count = len(ended_items)
    if count == 0:
        return True

    title = f"[sale_end_check] セール終了 {count}件 を検出"
    lines: list[str] = []
    for item in ended_items[:10]:
        work_id = item.get("work_id", "?")
        end_date = item.get("sale_end_date", "?")
        new_status = item.get("new_status", "?")
        lines.append(f"  - {work_id} | end={end_date} | → {new_status}")
    if count > 10:
        lines.append(f"  ... 他 {count - 10}件")

    return send_slack_block(title, lines)
