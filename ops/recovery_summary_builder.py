from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from monitoring.kpi_snapshot_reader import extract_kpi_summary, load_latest_kpi_snapshot
from monitoring.health_score_builder import build_health_score
from monitoring.run_anomaly_check import run_check
from pipelines.retry_queue_store import list_queue_items
from reporting.artifact_index_builder import (
    DEFAULT_ARCHIVE_DIR,
    DEFAULT_REPORT_DIR,
    build_artifact_index,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_retry_summary() -> dict[str, Any]:
    rows = list_queue_items()
    counter = Counter(str(row.get("retry_status", "unknown")) for row in rows)
    return {
        "total": len(rows),
        "queued": counter.get("queued", 0),
        "retrying": counter.get("retrying", 0),
        "resolved": counter.get("resolved", 0),
        "give_up": counter.get("give_up", 0),
    }


def _build_anomaly_summary() -> dict[str, Any]:
    try:
        result = run_check(report_dir=DEFAULT_REPORT_DIR)
        summary = result.get("summary", {}) if isinstance(result, dict) else {}
        latest_report = result.get("latest_report") or {}
        return {
            "overall": str(summary.get("overall_severity", "UNKNOWN")),
            "alert_count": int(summary.get("alert_count", 0)),
            "warning_count": int(summary.get("warning_count", 0)),
            "critical_count": int(summary.get("critical_count", 0)),
            "smoke_failed_count": int(result.get("smoke_failed_count", 0)),
            "failed_count": int(latest_report.get("failed_count", 0)),
            "latest_report_path": str(result.get("latest_report_path", "")),
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "overall": "UNKNOWN",
            "alert_count": 0,
            "warning_count": 0,
            "critical_count": 0,
            "smoke_failed_count": 0,
            "failed_count": 0,
            "latest_report_path": None,
            "error": str(exc),
        }


def _build_next_actions(summary: dict[str, Any]) -> list[str]:
    actions: list[str] = []

    anomaly = summary.get("anomaly", {})
    retry = summary.get("retry_queue", {})
    artifacts = summary.get("artifacts", {})

    anomaly_overall = str(anomaly.get("overall", "UNKNOWN"))
    queued = int(retry.get("queued", 0))
    archive = artifacts.get("latest_archive")

    if anomaly_overall == "OK":
        actions.append("通常運用継続可")
    elif anomaly_overall == "WARNING":
        actions.append("anomaly 警告あり。daily_report と anomaly ログ確認推奨")
    elif anomaly_overall == "CRITICAL":
        actions.append("anomaly が CRITICAL。一次復旧手順を優先実施")
    else:
        actions.append("anomaly 状態が不明。monitoring.run_anomaly_check の再実行推奨")

    if queued > 0:
        actions.append("retry queue の確認推奨")

    if not archive:
        actions.append("バックアップ実行推奨")

    if not actions:
        actions.append("特記事項なし")

    return actions


def _merge_kpi_snapshot(summary: dict[str, Any], snapshot: dict | None) -> dict[str, Any]:
    """KPI snapshot がある場合は主要指標を summary に反映する。"""
    if not snapshot:
        return summary

    kpi = extract_kpi_summary(snapshot)
    summary["kpi_summary"] = kpi

    anomaly = summary.get("anomaly") if isinstance(summary.get("anomaly"), dict) else {}
    retry = summary.get("retry_queue") if isinstance(summary.get("retry_queue"), dict) else {}

    kpi_anomaly = kpi.get("anomaly_overall")
    if kpi_anomaly and kpi_anomaly != "N/A":
        anomaly["overall"] = kpi_anomaly
    anomaly["alert_count"] = int(kpi.get("alert_total", anomaly.get("alert_count", 0)) or 0)

    retry["queued"] = int(kpi.get("retry_queued_count", retry.get("queued", 0)) or 0)
    summary["retry_queue"] = retry
    summary["anomaly"] = anomaly

    latest_archive = kpi.get("latest_archive")
    if latest_archive:
        summary["latest_archive"] = latest_archive

    summary["success_count"] = int(kpi.get("success_count", 0) or 0)
    summary["skipped_count"] = int(kpi.get("skipped_count", 0) or 0)
    summary["failed_count"] = int(kpi.get("failed_count", 0) or 0)
    summary["combined_count"] = int(kpi.get("combined_count", 0) or 0)
    summary["price_only_count"] = int(kpi.get("price_only_count", 0) or 0)
    summary["release_only_count"] = int(kpi.get("release_only_count", 0) or 0)

    hs = summary.get("health_score") if isinstance(summary.get("health_score"), dict) else {}
    kpi_score = kpi.get("health_score")
    kpi_grade = kpi.get("health_grade")
    if kpi_score not in (None, "N/A"):
        hs["score"] = kpi_score
    if kpi_grade not in (None, "N/A"):
        hs["grade"] = kpi_grade
    summary["health_score"] = hs

    return summary


def build_recovery_summary() -> dict:
    """復旧一次確認向けサマリーを生成する。"""
    artifacts = build_artifact_index(report_dir=DEFAULT_REPORT_DIR, archive_dir=DEFAULT_ARCHIVE_DIR)
    retry_summary = _build_retry_summary()
    anomaly_summary = _build_anomaly_summary()

    summary: dict[str, Any] = {
        "generated_at": _now_iso(),
        "latest_daily_report": artifacts.get("latest_daily_report_json"),
        "latest_weekly_report": artifacts.get("latest_weekly_report_json"),
        "latest_monthly_report": artifacts.get("latest_monthly_report_json"),
        "latest_dashboard": artifacts.get("latest_dashboard"),
        "latest_weekly_dashboard": artifacts.get("latest_weekly_dashboard"),
        "latest_archive": artifacts.get("latest_archive"),
        "retry_queue": retry_summary,
        "anomaly": anomaly_summary,
        "artifacts": artifacts,
    }

    summary["health_score"] = build_health_score(summary)
    summary = _merge_kpi_snapshot(summary, load_latest_kpi_snapshot())
    summary["next_actions"] = _build_next_actions(summary)
    return summary


def format_recovery_summary(summary: dict) -> str:
    """人間向けの復旧サマリー文字列を返す。"""
    retry = summary.get("retry_queue", {})
    anomaly = summary.get("anomaly", {})

    lines: list[str] = []
    lines.append("=" * 76)
    lines.append("AI Media OS Recovery Summary")
    lines.append("=" * 76)
    lines.append(f"generated_at: {summary.get('generated_at', '')}")
    lines.append("")
    lines.append("Latest Artifacts")
    lines.append(f"- latest_daily_report:    {summary.get('latest_daily_report')}")
    lines.append(f"- latest_weekly_report:   {summary.get('latest_weekly_report')}")
    lines.append(f"- latest_monthly_report:  {summary.get('latest_monthly_report')}")
    lines.append(f"- latest_dashboard:       {summary.get('latest_dashboard')}")
    lines.append(f"- latest_weekly_dashboard:{summary.get('latest_weekly_dashboard')}")
    lines.append(f"- latest_archive:         {summary.get('latest_archive')}")
    lines.append("")
    lines.append("Retry Queue")
    lines.append(f"- total:    {retry.get('total', 0)}")
    lines.append(f"- queued:   {retry.get('queued', 0)}")
    lines.append(f"- retrying: {retry.get('retrying', 0)}")
    lines.append(f"- resolved: {retry.get('resolved', 0)}")
    lines.append(f"- give_up:  {retry.get('give_up', 0)}")
    lines.append("")
    lines.append("Anomaly")
    lines.append(f"- latest_overall:   {anomaly.get('overall')}")
    lines.append(f"- alerts:           total={anomaly.get('alert_count', 0)} warning={anomaly.get('warning_count', 0)} critical={anomaly.get('critical_count', 0)}")
    lines.append(f"- smoke_failed:     {anomaly.get('smoke_failed_count', 0)}")
    lines.append(f"- failed_count:     {anomaly.get('failed_count', 0)}")
    lines.append(f"- latest_report:    {anomaly.get('latest_report_path')}")
    if anomaly.get("error"):
        lines.append(f"- error: {anomaly.get('error')}")
    lines.append("")

    hs = summary.get("health_score") or {}
    lines.append("Health Score")
    lines.append(f"- score: {hs.get('score', 'N/A')}  grade: {hs.get('grade', 'N/A')}")
    deductions = hs.get("deductions") or []
    if deductions:
        for d in deductions:
            lines.append(f"  [{d.get('deduction'):+d}] {d.get('reason')}")
    else:
        lines.append("  減点なし")
    lines.append("")
    lines.append("Next Actions")
    for action in summary.get("next_actions", []):
        lines.append(f"- {action}")

    return "\n".join(lines)