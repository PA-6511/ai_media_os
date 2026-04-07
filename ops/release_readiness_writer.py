from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = BASE_DIR / "data" / "reports"
DEFAULT_KPI_DIR = BASE_DIR / "data" / "kpi"
DEFAULT_JSON_PATH = DEFAULT_REPORT_DIR / "release_readiness_latest.json"
DEFAULT_MD_PATH = DEFAULT_REPORT_DIR / "release_readiness_latest.md"
DEFAULT_HISTORY_PATH = DEFAULT_KPI_DIR / "release_readiness_history.jsonl"


def _to_history_row(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": summary.get("generated_at"),
        "decision": summary.get("decision"),
        "anomaly_overall": summary.get("anomaly_overall"),
        "health_score": summary.get("health_score"),
        "health_grade": summary.get("health_grade"),
        "retry_queued": summary.get("retry_queued"),
        "integrity_overall": summary.get("integrity_overall"),
        "latest_daily_report": summary.get("latest_daily_report"),
        "latest_archive": summary.get("latest_archive"),
        "recommended_action": summary.get("recommended_action"),
    }


def append_release_readiness_history(summary: dict, output_path: Path | None = None) -> str:
    """release readiness の履歴を JSONL へ1件追記する。"""
    path = output_path or DEFAULT_HISTORY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    row = _to_history_row(summary)
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(row, ensure_ascii=False) + "\n")

    return str(path)


def write_release_readiness_json(summary: dict, output_path: Path | None = None) -> str:
    """release readiness サマリーを JSON で保存する。"""
    path = output_path or DEFAULT_JSON_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def _line(value: Any, fallback: str = "N/A") -> str:
    if value is None or value == "":
        return fallback
    return str(value)


def write_release_readiness_md(summary: dict, output_path: Path | None = None) -> str:
    """release readiness サマリーを Markdown で保存する。"""
    path = output_path or DEFAULT_MD_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    reasons = summary.get("reasons") if isinstance(summary.get("reasons"), list) else []
    signals = summary.get("signals") if isinstance(summary.get("signals"), dict) else {}

    lines: list[str] = []
    lines.append("# AI Media OS Release Readiness")
    lines.append("")
    lines.append(f"generated_at: {_line(summary.get('generated_at'))}")
    lines.append(f"decision: {_line(summary.get('decision'))}")
    lines.append("")
    lines.append("## Core Signals")
    lines.append("")
    lines.append(f"- anomaly_overall: {_line(summary.get('anomaly_overall'))}")
    lines.append(f"- health_score: {_line(summary.get('health_score'))}")
    lines.append(f"- health_grade: {_line(summary.get('health_grade'))}")
    lines.append(f"- retry_queued: {_line(summary.get('retry_queued'))}")
    lines.append(f"- integrity_overall: {_line(summary.get('integrity_overall'))}")
    lines.append(f"- latest_daily_report: {_line(summary.get('latest_daily_report'))}")
    lines.append(f"- latest_archive: {_line(summary.get('latest_archive'))}")
    lines.append("")
    lines.append("## Reasons")
    lines.append("")
    if reasons:
        for reason in reasons:
            lines.append(f"- {_line(reason)}")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("## Recommended Action")
    lines.append("")
    lines.append(f"- {_line(summary.get('recommended_action'))}")
    lines.append("")
    lines.append("## Checklist / Integrity Details")
    lines.append("")
    lines.append(f"- checklist_anomaly_overall: {_line(signals.get('checklist_anomaly_overall'))}")
    lines.append(f"- checklist_retry_queued_count: {_line(signals.get('checklist_retry_queued_count'))}")
    lines.append(f"- checklist_daily_report_exists: {_line(signals.get('checklist_daily_report_exists'))}")
    lines.append(f"- checklist_dashboard_exists: {_line(signals.get('checklist_dashboard_exists'))}")
    lines.append(f"- checklist_archive_exists: {_line(signals.get('checklist_archive_exists'))}")
    lines.append(f"- integrity_pass_count: {_line(signals.get('integrity_pass_count'))}")
    lines.append(f"- integrity_warning_count: {_line(signals.get('integrity_warning_count'))}")
    lines.append(f"- integrity_fail_count: {_line(signals.get('integrity_fail_count'))}")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
