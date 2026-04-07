from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import BASE_DIR, DEFAULT_REPORT_DIR


DEFAULT_RELEASE_READINESS_JSON_PATH = DEFAULT_REPORT_DIR / "release_readiness_latest.json"
DEFAULT_STATUS_LIGHT_JSON_PATH = DEFAULT_REPORT_DIR / "ops_status_light_latest.json"
DEFAULT_HEADER_JSON_PATH = DEFAULT_REPORT_DIR / "ops_header_latest.json"
DEFAULT_ALERT_CENTER_JSON_PATH = DEFAULT_REPORT_DIR / "ops_alert_center_latest.json"
SCHEMA_VERSION = "1.0"

SEVERITY_PRIORITY = {
    "ok": 0,
    "info": 1,
    "review": 2,
    "warning": 3,
    "critical": 4,
}


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


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_iso(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _max_iso(values: list[Any]) -> str | None:
    latest: datetime | None = None
    for value in values:
        dt = _parse_iso(value)
        if dt is None:
            continue
        if latest is None or dt > latest:
            latest = dt
    return latest.isoformat() if latest else None


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


def _severity_from_alert_center(alert_center: dict[str, Any]) -> str:
    overall = str(alert_center.get("overall") or "").strip().lower()
    if overall in {"critical", "warning", "review", "ok", "info"}:
        return overall
    return "info"


def _severity_from_anomaly(anomaly_overall: str) -> str:
    if anomaly_overall in {"CRITICAL", "FAIL"}:
        return "critical"
    if anomaly_overall in {"WARNING"}:
        return "warning"
    if anomaly_overall in {"REVIEW"}:
        return "review"
    if anomaly_overall in {"OK", "PASS", "RELEASE"}:
        return "ok"
    return "info"


def _max_severity(*levels: str) -> str:
    best = "info"
    for level in levels:
        key = str(level or "info").lower()
        if SEVERITY_PRIORITY.get(key, 1) > SEVERITY_PRIORITY.get(best, 1):
            best = key
    return best


def _decision_from_inputs(readiness_decision: str, severity: str, health_score: int | None) -> str:
    rd = readiness_decision.lower()

    if severity == "critical":
        return "hold"
    if severity in {"warning", "review"}:
        return "review"
    if health_score is not None and health_score < 50:
        return "review"

    if rd in {"hold", "block", "critical"}:
        return "hold"
    if rd in {"review", "warning"}:
        return "review"
    if rd in {"release", "ok", "pass"}:
        return "release"
    return "review"


def _reason(decision: str, anomaly_overall: str, severity: str, alert_count: int) -> str:
    if severity == "critical":
        return "critical signal detected in anomaly/alerts"
    if severity in {"warning", "review"}:
        return f"anomaly overall is {anomaly_overall} and alerts={alert_count}"
    if decision == "release":
        return "readiness and health signals are within release range"
    return "insufficient signal quality, review recommended"


def _recommended_action(decision: str, readiness_action: str) -> str:
    if readiness_action:
        return readiness_action
    if decision == "hold":
        return "critical alerts を解消後に再判定"
    if decision == "review":
        return "担当レビュー後に再判定"
    return "通常運用を継続"


def build_ops_decision_summary() -> dict[str, Any]:
    release_readiness = _safe_read_json(DEFAULT_RELEASE_READINESS_JSON_PATH)
    status_light = _safe_read_json(DEFAULT_STATUS_LIGHT_JSON_PATH)
    header = _safe_read_json(DEFAULT_HEADER_JSON_PATH)
    alert_center = _safe_read_json(DEFAULT_ALERT_CENTER_JSON_PATH)

    health_score_raw = status_light.get("health_score")
    if health_score_raw is None:
        health_score_raw = header.get("health_score")
    health_score = _coerce_int(health_score_raw, 0) if health_score_raw is not None else None

    health_grade = str(status_light.get("health_grade") or header.get("health_grade") or "N/A")
    anomaly_overall = str(status_light.get("anomaly_overall") or header.get("anomaly_overall") or "N/A").upper()
    alert_count = _coerce_int((alert_center.get("summary") or {}).get("alert_count"), 0)
    readiness_decision = str(release_readiness.get("decision") or status_light.get("decision") or "review")

    severity = _max_severity(
        _severity_from_alert_center(alert_center),
        _severity_from_anomaly(anomaly_overall),
    )
    decision = _decision_from_inputs(readiness_decision, severity, health_score)

    readiness_action = str(release_readiness.get("recommended_action") or "").strip()
    recommended_action = _recommended_action(decision, readiness_action)

    updated_at = _max_iso(
        [
            release_readiness.get("generated_at"),
            status_light.get("generated_at"),
            header.get("generated_at"),
            alert_center.get("generated_at"),
        ]
    )

    sources = {
        "release_readiness": _source_meta(DEFAULT_RELEASE_READINESS_JSON_PATH, release_readiness),
        "status_light": _source_meta(DEFAULT_STATUS_LIGHT_JSON_PATH, status_light),
        "header": _source_meta(DEFAULT_HEADER_JSON_PATH, header),
        "alert_center": _source_meta(DEFAULT_ALERT_CENTER_JSON_PATH, alert_center),
    }
    missing_source_keys = [key for key, meta in sources.items() if not bool(meta.get("exists"))]
    partial = any(not bool(meta.get("loaded")) for meta in sources.values())

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "decision": decision,
        "severity": severity,
        "reason": _reason(decision, anomaly_overall, severity, alert_count),
        "recommended_action": recommended_action,
        "health_score": health_score,
        "health_grade": health_grade,
        "anomaly_overall": anomaly_overall,
        "alert_count": alert_count,
        "updated_at": updated_at or _now_iso(),
        "signals": {
            "readiness_decision": readiness_decision,
            "alert_center_overall": str(alert_center.get("overall") or "N/A"),
        },
        "status": {
            "partial": partial,
            "ready": len(missing_source_keys) == 0,
            "missing_source_keys": missing_source_keys,
            "fail_safe": True,
        },
        "sources": sources,
    }