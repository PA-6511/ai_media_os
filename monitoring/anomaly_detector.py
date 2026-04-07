from __future__ import annotations

from typing import Any

from monitoring.alert_thresholds import get_default_thresholds
from monitoring.anomaly_filters import filter_real_failed_slugs


def _build_alert(
    *,
    rule_id: str,
    severity: str,
    message: str,
    source: str,
    value: Any,
    threshold: Any,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Slack 連携しやすい標準アラート構造を作る。"""
    return {
        "rule_id": rule_id,
        "severity": severity,
        "message": message,
        "source": source,
        "value": value,
        "threshold": threshold,
        "details": details or {},
    }


def _all_signal_zero_streak_days(report_history: list[dict[str, Any]]) -> int:
    """全 signal (combined/price_only/release_only) が 0 の連続日数を数える。"""
    if not report_history:
        return 0

    streak = 0
    for report in reversed(report_history):
        combined = int(report.get("combined_count", 0) or 0)
        price_only = int(report.get("price_only_count", 0) or 0)
        release_only = int(report.get("release_only_count", 0) or 0)

        if combined == 0 and price_only == 0 and release_only == 0:
            streak += 1
        else:
            break

    return streak


def detect_failed_count_anomaly(
    report: dict[str, Any],
    thresholds: dict[str, Any],
) -> list[dict[str, Any]]:
    """failed_count の異常を検知する (fixture/test 除外後)。"""
    alerts: list[dict[str, Any]] = []

    failed_slugs = report.get("failed_slugs", [])
    if not isinstance(failed_slugs, list):
        failed_slugs = []

    raw_failed_count = int(report.get("failed_count", len(failed_slugs)) or 0)
    real_failed_slugs = filter_real_failed_slugs([str(x) for x in failed_slugs])
    real_failed_count = len(real_failed_slugs)

    failed_warning = int(thresholds["failed_count"]["warning"])
    failed_critical = int(thresholds["failed_count"]["critical"])

    details = {
        "raw_failed_count": raw_failed_count,
        "real_failed_count": real_failed_count,
        "excluded_fixture_count": max(raw_failed_count - real_failed_count, 0),
        "real_failed_slugs": real_failed_slugs[:20],
    }

    if real_failed_count >= failed_critical:
        alerts.append(
            _build_alert(
                rule_id="failed_count_real",
                severity="CRITICAL",
                message=(
                    "real failed count exceeded critical threshold: "
                    f"{real_failed_count} >= {failed_critical}"
                ),
                source="daily_report",
                value=real_failed_count,
                threshold={"warning": failed_warning, "critical": failed_critical},
                details=details,
            )
        )
    elif real_failed_count >= failed_warning:
        alerts.append(
            _build_alert(
                rule_id="failed_count_real",
                severity="WARNING",
                message=(
                    "real failed count exceeded warning threshold: "
                    f"{real_failed_count} >= {failed_warning}"
                ),
                source="daily_report",
                value=real_failed_count,
                threshold={"warning": failed_warning, "critical": failed_critical},
                details=details,
            )
        )

    return alerts


def detect_retry_queue_anomaly(
    report: dict[str, Any],
    thresholds: dict[str, Any],
) -> list[dict[str, Any]]:
    """retry queue の異常を検知する。"""
    alerts: list[dict[str, Any]] = []

    retry_queued_count = int(report.get("retry_queued_count", 0) or 0)
    retry_warning = int(thresholds["retry_queued_count"]["warning"])
    retry_critical = int(thresholds["retry_queued_count"]["critical"])

    if retry_queued_count >= retry_critical:
        alerts.append(
            _build_alert(
                rule_id="retry_queued_count",
                severity="CRITICAL",
                message=(
                    "retry queued count exceeded critical threshold: "
                    f"{retry_queued_count} >= {retry_critical}"
                ),
                source="daily_report",
                value=retry_queued_count,
                threshold={"warning": retry_warning, "critical": retry_critical},
            )
        )
    elif retry_queued_count >= retry_warning:
        alerts.append(
            _build_alert(
                rule_id="retry_queued_count",
                severity="WARNING",
                message=(
                    "retry queued count exceeded warning threshold: "
                    f"{retry_queued_count} >= {retry_warning}"
                ),
                source="daily_report",
                value=retry_queued_count,
                threshold={"warning": retry_warning, "critical": retry_critical},
            )
        )

    return alerts


def detect_smoke_test_anomaly(
    smoke_failed_count: int,
    thresholds: dict[str, Any],
) -> list[dict[str, Any]]:
    """smoke test fail 件数の異常を検知する。"""
    alerts: list[dict[str, Any]] = []

    smoke_warning = int(thresholds["smoke_test_failed"]["warning"])
    smoke_critical = int(thresholds["smoke_test_failed"]["critical"])

    if smoke_failed_count >= smoke_critical:
        alerts.append(
            _build_alert(
                rule_id="smoke_failed_count",
                severity="CRITICAL",
                message=(
                    "smoke test failed count exceeded critical threshold: "
                    f"{smoke_failed_count} >= {smoke_critical}"
                ),
                source="smoke_test.log",
                value=smoke_failed_count,
                threshold={"warning": smoke_warning, "critical": smoke_critical},
            )
        )
    elif smoke_failed_count >= smoke_warning:
        alerts.append(
            _build_alert(
                rule_id="smoke_failed_count",
                severity="WARNING",
                message=(
                    "smoke test failed count exceeded warning threshold: "
                    f"{smoke_failed_count} >= {smoke_warning}"
                ),
                source="smoke_test.log",
                value=smoke_failed_count,
                threshold={"warning": smoke_warning, "critical": smoke_critical},
            )
        )

    return alerts


def detect_all_signal_zero_streak(
    report_history: list[dict[str, Any]],
    thresholds: dict[str, Any],
) -> list[dict[str, Any]]:
    """全 signal 停止状態の連続日数を検知する。"""
    alerts: list[dict[str, Any]] = []

    warning_days = int(thresholds["all_signal_zero_streak"]["warning_days"])
    streak_days = _all_signal_zero_streak_days(report_history)

    if streak_days >= warning_days:
        latest = report_history[-1] if report_history else {}
        alerts.append(
            _build_alert(
                rule_id="all_signal_zero_streak",
                severity="WARNING",
                message=(
                    "all signal counts stayed zero for consecutive days: "
                    f"{streak_days} >= {warning_days}"
                ),
                source="daily_report_history",
                value=streak_days,
                threshold={"warning_days": warning_days},
                details={
                    "latest_report_date": latest.get("report_date", ""),
                    "recent_report_count": len(report_history),
                    "latest_counts": {
                        "combined_count": int(latest.get("combined_count", 0) or 0),
                        "price_only_count": int(latest.get("price_only_count", 0) or 0),
                        "release_only_count": int(latest.get("release_only_count", 0) or 0),
                    },
                },
            )
        )

    return alerts


def detect_anomalies(
    report: dict[str, Any],
    thresholds: dict[str, Any] | None = None,
    report_history: list[dict[str, Any]] | None = None,
    smoke_failed_count: int = 0,
) -> list[dict[str, Any]]:
    """日次レポートおよび補助情報から異常を検知する。"""
    th = thresholds or get_default_thresholds()
    history = report_history or [report]

    alerts: list[dict[str, Any]] = []
    alerts.extend(detect_failed_count_anomaly(report, th))
    alerts.extend(detect_retry_queue_anomaly(report, th))
    alerts.extend(detect_smoke_test_anomaly(smoke_failed_count, th))
    alerts.extend(detect_all_signal_zero_streak(history, th))

    return alerts


def summarize_alerts(alerts: list[dict[str, Any]]) -> dict[str, Any]:
    """アラート一覧を集約し、通知しやすいサマリーを返す。"""
    warning_count = sum(1 for a in alerts if a.get("severity") == "WARNING")
    critical_count = sum(1 for a in alerts if a.get("severity") == "CRITICAL")

    if critical_count > 0:
        overall = "CRITICAL"
    elif warning_count > 0:
        overall = "WARNING"
    else:
        overall = "OK"

    return {
        "overall_severity": overall,
        "alert_count": len(alerts),
        "warning_count": warning_count,
        "critical_count": critical_count,
        "alerts": alerts,
    }
