from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from monitoring.run_anomaly_check import load_latest_daily_report, run_check
from ops.recovery_summary_builder import build_recovery_summary
from reporting.artifact_index_builder import (
    DEFAULT_ARCHIVE_DIR,
    DEFAULT_REPORT_DIR,
    build_artifact_index,
)
from reporting.monthly_dashboard_builder import load_latest_monthly_report
from reporting.weekly_dashboard_builder import load_latest_weekly_report


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_load_latest_monthly_path() -> str | None:
    try:
        _, path = load_latest_monthly_report(DEFAULT_REPORT_DIR)
        return str(path)
    except Exception:
        return None


def _safe_load_latest_weekly_path() -> str | None:
    try:
        _, path = load_latest_weekly_report(DEFAULT_REPORT_DIR)
        return str(path)
    except Exception:
        return None


def build_kpi_snapshot() -> dict:
    """現在の主要 KPI を軽量スナップショット1件にまとめる。"""
    recovery = build_recovery_summary()
    artifact_index = build_artifact_index(DEFAULT_REPORT_DIR, DEFAULT_ARCHIVE_DIR)
    anomaly_result = run_check(report_dir=DEFAULT_REPORT_DIR)
    latest_daily_report, latest_daily_path = load_latest_daily_report(DEFAULT_REPORT_DIR)

    anomaly_summary = anomaly_result.get("summary", {}) if isinstance(anomaly_result, dict) else {}
    health = recovery.get("health_score") or {}

    snapshot: dict[str, Any] = {
        "generated_at": _now_iso(),
        "latest_daily_report": str(latest_daily_path),
        "latest_weekly_report": _safe_load_latest_weekly_path(),
        "latest_monthly_report": _safe_load_latest_monthly_path(),
        "latest_archive": artifact_index.get("latest_archive"),
        "archive_count": int(artifact_index.get("archive_count", 0)),
        "anomaly_overall": str((recovery.get("anomaly") or {}).get("overall", "UNKNOWN")),
        "alert_total": int(anomaly_summary.get("alert_count", 0)),
        "health_score": int(health.get("score", 0)),
        "health_grade": str(health.get("grade", "E")),
        "success_count": int(latest_daily_report.get("success_count", 0)),
        "skipped_count": int(latest_daily_report.get("skipped_count", 0)),
        "failed_count": int(latest_daily_report.get("failed_count", 0)),
        "draft_count": int(latest_daily_report.get("draft_count", 0)),
        "retry_queued_count": int(latest_daily_report.get("retry_queued_count", 0)),
        "combined_count": int(latest_daily_report.get("combined_count", 0)),
        "price_only_count": int(latest_daily_report.get("price_only_count", 0)),
        "release_only_count": int(latest_daily_report.get("release_only_count", 0)),
        "daily_metrics": {
            "report_date": latest_daily_report.get("report_date"),
            "success_count": int(latest_daily_report.get("success_count", 0)),
            "skipped_count": int(latest_daily_report.get("skipped_count", 0)),
            "failed_count": int(latest_daily_report.get("failed_count", 0)),
            "draft_count": int(latest_daily_report.get("draft_count", 0)),
            "retry_queued_count": int(latest_daily_report.get("retry_queued_count", 0)),
            "combined_count": int(latest_daily_report.get("combined_count", 0)),
            "price_only_count": int(latest_daily_report.get("price_only_count", 0)),
            "release_only_count": int(latest_daily_report.get("release_only_count", 0)),
        },
        "weekly_metrics": {
            "latest_weekly_report": _safe_load_latest_weekly_path(),
        },
        "monthly_metrics": {
            "latest_monthly_report": _safe_load_latest_monthly_path(),
        },
        "anomaly_metrics": {
            "overall": str((recovery.get("anomaly") or {}).get("overall", "UNKNOWN")),
            "alert_total": int(anomaly_summary.get("alert_count", 0)),
            "warning_count": int(anomaly_summary.get("warning_count", 0)),
            "critical_count": int(anomaly_summary.get("critical_count", 0)),
        },
        "health_metrics": {
            "score": int(health.get("score", 0)),
            "grade": str(health.get("grade", "E")),
            "deductions": health.get("deductions", []),
        },
        "artifact_metrics": {
            "latest_archive": artifact_index.get("latest_archive"),
            "archive_count": int(artifact_index.get("archive_count", 0)),
            "latest_dashboard": artifact_index.get("latest_dashboard"),
            "latest_monthly_dashboard": artifact_index.get("latest_monthly_dashboard"),
        },
    }

    return snapshot
