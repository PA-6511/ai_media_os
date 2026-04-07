from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from monitoring.slack_notifier import send_slack_block


DEFAULT_NOTIFY_CONFIG: dict[str, bool] = {
    "notify_on_ok": False,
    "notify_on_warning": True,
    "notify_on_critical": True,
}


def should_notify_anomaly(result: dict[str, Any], config: dict[str, bool] | None = None) -> bool:
    """通知可否を判定する。"""
    cfg = {**DEFAULT_NOTIFY_CONFIG, **(config or {})}
    summary = result.get("summary", {})
    overall = str(summary.get("overall_severity", "OK")).upper()

    if overall == "CRITICAL":
        return bool(cfg.get("notify_on_critical", True))
    if overall == "WARNING":
        return bool(cfg.get("notify_on_warning", True))
    return bool(cfg.get("notify_on_ok", False))


def build_anomaly_lines(result: dict[str, Any], max_alerts: int = 3) -> list[str]:
    """Slack通知本文の行配列を作る。"""
    summary = result.get("summary", {})
    alerts = summary.get("alerts", [])
    if not isinstance(alerts, list):
        alerts = []

    latest_report = Path(str(result.get("latest_report_path", ""))).name
    executed_at = str(result.get("executed_at", datetime.now(timezone.utc).isoformat()))

    lines: list[str] = [
        f"- executed_at: {executed_at}",
        f"- latest_report: {latest_report}",
        f"- total alerts: {summary.get('alert_count', 0)}",
        f"- warning: {summary.get('warning_count', 0)}",
        f"- critical: {summary.get('critical_count', 0)}",
    ]

    top = alerts[:max_alerts]
    if top:
        lines.append("- alerts:")
        for alert in top:
            lines.append(
                "  - "
                f"{alert.get('rule_id', '')}: {alert.get('message', '')} "
                f"(severity={alert.get('severity', '')})"
            )

    return lines


def notify_anomaly_result(
    result: dict[str, Any],
    config: dict[str, bool] | None = None,
) -> bool:
    """異常検知結果を Slack に通知する。"""
    if not should_notify_anomaly(result, config=config):
        return False

    summary = result.get("summary", {})
    overall = str(summary.get("overall_severity", "OK")).upper()
    title = f"[ANOMALY CHECK] {overall}"
    lines = build_anomaly_lines(result)

    # Slack未設定や送信失敗時も False を返すだけで、例外は呼び出し元へ上げない。
    return send_slack_block(title, lines)
