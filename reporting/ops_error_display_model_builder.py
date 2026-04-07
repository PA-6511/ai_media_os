from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import BASE_DIR, DEFAULT_REPORT_DIR


DEFAULT_ALERT_CENTER_PATH = DEFAULT_REPORT_DIR / "ops_alert_center_latest.json"
DEFAULT_DECISION_SUMMARY_PATH = DEFAULT_REPORT_DIR / "ops_decision_summary_latest.json"
DEFAULT_GUI_INTEGRITY_PATH = DEFAULT_REPORT_DIR / "ops_gui_integrity_latest.json"
DEFAULT_GUI_HEALTH_PATH = DEFAULT_REPORT_DIR / "ops_gui_health_latest.json"
DEFAULT_MOCK_API_PATH = DEFAULT_REPORT_DIR / "mock_api_home_latest.json"
SCHEMA_VERSION = "1.0"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR)).replace("\\", "/")
    except ValueError:
        return str(path)


def _safe_read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _source_meta(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    updated_at = None
    if path.exists() and path.is_file():
        updated_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    return {
        "path": _normalize_path(path),
        "exists": path.exists() and path.is_file(),
        "loaded": bool(payload),
        "updated_at": updated_at,
    }


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _lower(value: Any) -> str:
    return str(value or "").strip().lower()


def _upper(value: Any) -> str:
    return str(value or "").strip().upper()


def _model(severity: str, badge: str, color_hint: str, title_template: str, action_template: str) -> dict[str, Any]:
    return {
        "severity": severity,
        "badge": badge,
        "color_hint": color_hint,
        "title_template": title_template,
        "action_template": action_template,
    }


def build_ops_error_display_model() -> dict[str, Any]:
    alert_center = _safe_read_json(DEFAULT_ALERT_CENTER_PATH)
    decision_summary = _safe_read_json(DEFAULT_DECISION_SUMMARY_PATH)
    gui_integrity = _safe_read_json(DEFAULT_GUI_INTEGRITY_PATH)
    gui_health = _safe_read_json(DEFAULT_GUI_HEALTH_PATH)

    models = [
        _model(
            severity="critical",
            badge="CRITICAL",
            color_hint="red",
            title_template="Critical Issue Detected",
            action_template="即時対応してください。復旧後に再チェックを実行してください。",
        ),
        _model(
            severity="warning",
            badge="WARNING",
            color_hint="amber",
            title_template="Warning Detected",
            action_template="詳細を確認し、必要な修正を実施してください。",
        ),
        _model(
            severity="review",
            badge="REVIEW",
            color_hint="blue",
            title_template="Review Required",
            action_template="判断保留です。担当者レビュー後に最終判断してください。",
        ),
        _model(
            severity="info",
            badge="INFO",
            color_hint="teal",
            title_template="Information",
            action_template="状況を確認し、通常運用を継続してください。",
        ),
        _model(
            severity="ok",
            badge="OK",
            color_hint="green",
            title_template="All Systems Nominal",
            action_template="追加対応は不要です。定期監視を継続してください。",
        ),
    ]

    alert_summary = alert_center.get("summary") if isinstance(alert_center.get("summary"), dict) else {}
    critical_count = _to_int(alert_summary.get("critical_count"), 0)
    warning_count = _to_int(alert_summary.get("warning_count"), 0)
    info_count = _to_int(alert_summary.get("info_count"), 0)

    anomaly_overall = _upper(gui_health.get("anomaly_overall") or (alert_center.get("signals") if isinstance(alert_center.get("signals"), dict) else {}).get("status_light", {}).get("anomaly_overall"))
    decision = _lower(decision_summary.get("decision"))
    decision_severity = _lower(decision_summary.get("severity"))
    integrity_overall = _upper(gui_integrity.get("overall"))
    retry_queued = _to_int((alert_center.get("signals") if isinstance(alert_center.get("signals"), dict) else {}).get("retry_queue", {}).get("queued"), 0)
    mock_api_missing = not (DEFAULT_MOCK_API_PATH.exists() and DEFAULT_MOCK_API_PATH.is_file())

    active_severities: list[str] = []
    active_reasons: list[str] = []

    if integrity_overall == "FAIL" or critical_count > 0 or anomaly_overall == "CRITICAL":
        active_severities.append("critical")
        active_reasons.append("integrity FAIL または critical alert/anomaly を検出")

    if integrity_overall == "WARNING" or warning_count > 0 or anomaly_overall == "WARNING" or retry_queued > 0 or mock_api_missing:
        active_severities.append("warning")
        active_reasons.append("warning/integrity warning/retry queue/mock api 状態を検出")

    if decision in {"review", "hold"} or decision_severity == "review":
        active_severities.append("review")
        active_reasons.append("readiness decision が review/hold")

    if info_count > 0:
        active_severities.append("info")
        active_reasons.append("informational alert を検出")

    if not active_severities:
        active_severities.append("ok")
        active_reasons.append("critical/warning/review 条件なし")

    deduped_severities: list[str] = []
    seen: set[str] = set()
    for severity in active_severities:
        if severity in seen:
            continue
        seen.add(severity)
        deduped_severities.append(severity)

    sources = {
        "alert_center": _source_meta(DEFAULT_ALERT_CENTER_PATH, alert_center),
        "decision_summary": _source_meta(DEFAULT_DECISION_SUMMARY_PATH, decision_summary),
        "gui_integrity": _source_meta(DEFAULT_GUI_INTEGRITY_PATH, gui_integrity),
        "gui_health": _source_meta(DEFAULT_GUI_HEALTH_PATH, gui_health),
        "mock_api": {
            "path": _normalize_path(DEFAULT_MOCK_API_PATH),
            "exists": DEFAULT_MOCK_API_PATH.exists() and DEFAULT_MOCK_API_PATH.is_file(),
            "loaded": DEFAULT_MOCK_API_PATH.exists() and DEFAULT_MOCK_API_PATH.is_file(),
            "updated_at": datetime.fromtimestamp(DEFAULT_MOCK_API_PATH.stat().st_mtime, tz=timezone.utc).isoformat() if DEFAULT_MOCK_API_PATH.exists() and DEFAULT_MOCK_API_PATH.is_file() else None,
        },
    }
    missing_source_keys = [key for key, meta in sources.items() if not bool(meta.get("exists"))]
    partial = any(not bool(meta.get("loaded")) for meta in sources.values())

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "models": models,
        "active": {
            "severities": deduped_severities,
            "reasons": active_reasons,
            "snapshot": {
                "anomaly_overall": anomaly_overall or "UNKNOWN",
                "decision": decision or "unknown",
                "decision_severity": decision_severity or "unknown",
                "integrity_overall": integrity_overall or "UNKNOWN",
                "retry_queued": retry_queued,
                "mock_api_missing": mock_api_missing,
                "critical_count": critical_count,
                "warning_count": warning_count,
                "info_count": info_count,
            },
        },
        "summary": {
            "model_count": len(models),
            "active_severity_count": len(deduped_severities),
        },
        "status": {
            "partial": partial,
            "ready": len(missing_source_keys) == 0,
            "missing_source_keys": missing_source_keys,
            "fail_safe": True,
        },
        "sources": sources,
    }
