from __future__ import annotations

from typing import Any

from config.ops_settings_loader import get_ops_setting
from monitoring.slack_notifier import send_slack_block
from ops.recovery_summary_builder import build_recovery_summary


def should_notify_ops_summary(summary: dict, settings: dict) -> bool:
    """ops summary 通知の要否を判定する。"""
    fail_count = int(summary.get("fail_count", 0))
    overall = str(summary.get("overall", "PASS"))
    anomaly_overall = str(summary.get("anomaly_overall", "UNKNOWN"))

    notify_on_pass = bool(settings.get("notify_on_pass", False))
    notify_on_fail = bool(settings.get("notify_on_fail", True))
    notify_on_warning = bool(settings.get("notify_on_warning", True))

    if fail_count > 0 or overall == "FAIL":
        return notify_on_fail

    if anomaly_overall in {"WARNING", "CRITICAL"}:
        return notify_on_warning

    return notify_on_pass


def build_ops_summary_lines(summary: dict) -> list[str]:
    """Slack 通知向けに ops summary の本文行を作る。"""
    lines: list[str] = []
    lines.append(f"overall: {summary.get('overall', 'UNKNOWN')}")
    lines.append(
        f"ops_result: PASS={summary.get('pass_count', 0)} "
        f"FAIL={summary.get('fail_count', 0)}"
    )
    lines.append(f"anomaly: {summary.get('anomaly_overall', 'UNKNOWN')}")
    lines.append(
        f"health_score: {summary.get('health_score', 'N/A')} "
        f"(grade {summary.get('health_grade', 'N/A')})"
    )
    lines.append(f"latest_daily_report: {summary.get('latest_daily_report')}")
    lines.append(f"latest_archive: {summary.get('latest_archive')}")
    lines.append(f"next_action: {summary.get('next_action')}")
    return lines


def _enrich_with_recovery(summary: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(summary)
    recovery = build_recovery_summary()

    anomaly = recovery.get("anomaly") or {}
    health = recovery.get("health_score") or {}
    next_actions = recovery.get("next_actions") or []

    if "anomaly_overall" not in enriched:
        enriched["anomaly_overall"] = anomaly.get("overall", "UNKNOWN")
    if "health_score" not in enriched:
        enriched["health_score"] = health.get("score", "N/A")
    if "health_grade" not in enriched:
        enriched["health_grade"] = health.get("grade", "N/A")
    if "latest_daily_report" not in enriched:
        enriched["latest_daily_report"] = recovery.get("latest_daily_report")
    if "latest_archive" not in enriched:
        enriched["latest_archive"] = recovery.get("latest_archive")
    if "next_action" not in enriched:
        enriched["next_action"] = next_actions[0] if next_actions else "特記事項なし"

    return enriched


def notify_ops_summary(summary: dict) -> bool:
    """ops cycle 要約を Slack 通知する。未設定時は安全にスキップする。"""
    settings = get_ops_setting("ops_summary_notify", {})
    if not isinstance(settings, dict):
        settings = {}

    try:
        enriched = _enrich_with_recovery(summary if isinstance(summary, dict) else {})
    except Exception:
        # recovery summary 取得失敗時も ops 本体を止めない。
        enriched = dict(summary) if isinstance(summary, dict) else {}
        enriched.setdefault("anomaly_overall", "UNKNOWN")
        enriched.setdefault("health_score", "N/A")
        enriched.setdefault("health_grade", "N/A")
        enriched.setdefault("latest_daily_report", None)
        enriched.setdefault("latest_archive", None)
        enriched.setdefault("next_action", "recovery summary 取得失敗。run_recovery_check 実行推奨")

    if not should_notify_ops_summary(enriched, settings):
        return False

    title = "AI Media OS Ops Summary"
    lines = build_ops_summary_lines(enriched)
    return send_slack_block(title, lines)
