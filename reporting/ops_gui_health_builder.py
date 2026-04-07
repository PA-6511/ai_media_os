from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import BASE_DIR, DEFAULT_REPORT_DIR


DEFAULT_STATUS_LIGHT_JSON_PATH = DEFAULT_REPORT_DIR / "ops_status_light_latest.json"
DEFAULT_HEADER_JSON_PATH = DEFAULT_REPORT_DIR / "ops_header_latest.json"
DEFAULT_CONFIG_SUMMARY_JSON_PATH = DEFAULT_REPORT_DIR / "ops_config_summary_latest.json"
DEFAULT_ALERT_CENTER_JSON_PATH = DEFAULT_REPORT_DIR / "ops_alert_center_latest.json"
DEFAULT_TIMESTAMPS_JSON_PATH = DEFAULT_REPORT_DIR / "ops_timestamps_latest.json"
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


def _coerce_int(value: Any, default: int | None = None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_iso(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
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


def _normalize_anomaly(value: Any) -> str:
    text = str(value or "").strip().upper()
    return text if text else "N/A"


def _is_ok(anomaly_overall: str, alert_count: int, health_score: int | None) -> bool:
    if anomaly_overall in {"CRITICAL", "FAIL"}:
        return False
    if alert_count > 0 and anomaly_overall in {"WARNING", "REVIEW"}:
        return False
    if health_score is not None and health_score < 50:
        return False
    return True


def build_ops_gui_health() -> dict[str, Any]:
    status_light = _safe_read_json(DEFAULT_STATUS_LIGHT_JSON_PATH)
    header = _safe_read_json(DEFAULT_HEADER_JSON_PATH)
    config_summary = _safe_read_json(DEFAULT_CONFIG_SUMMARY_JSON_PATH)
    alert_center = _safe_read_json(DEFAULT_ALERT_CENTER_JSON_PATH)
    timestamps = _safe_read_json(DEFAULT_TIMESTAMPS_JSON_PATH)

    health_score = _coerce_int(status_light.get("health_score"), None)
    health_grade = str(status_light.get("health_grade") or header.get("health_grade") or "N/A")
    anomaly_overall = _normalize_anomaly(status_light.get("anomaly_overall") or header.get("anomaly_overall"))
    alert_count = _coerce_int((alert_center.get("summary") or {}).get("alert_count"), 0) or 0

    updated_at = _max_iso(
        [
            status_light.get("generated_at"),
            header.get("generated_at"),
            header.get("last_updated"),
            config_summary.get("generated_at"),
            alert_center.get("generated_at"),
            timestamps.get("generated_at"),
        ]
    )

    sources = {
        "status_light": _source_meta(DEFAULT_STATUS_LIGHT_JSON_PATH, status_light),
        "header": _source_meta(DEFAULT_HEADER_JSON_PATH, header),
        "config_summary": _source_meta(DEFAULT_CONFIG_SUMMARY_JSON_PATH, config_summary),
        "alert_center": _source_meta(DEFAULT_ALERT_CENTER_JSON_PATH, alert_center),
        "timestamps": _source_meta(DEFAULT_TIMESTAMPS_JSON_PATH, timestamps),
    }

    missing_source_keys = [key for key, meta in sources.items() if not bool(meta.get("exists"))]
    partial = any(not bool(meta.get("loaded")) for meta in sources.values())

    return {
        "ok": _is_ok(anomaly_overall, alert_count, health_score),
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "health_score": health_score,
        "health_grade": health_grade,
        "anomaly_overall": anomaly_overall,
        "alert_count": alert_count,
        "updated_at": updated_at or _now_iso(),
        "ops_decision": str(status_light.get("decision") or "N/A"),
        "status": {
            "partial": partial,
            "ready": len(missing_source_keys) == 0,
            "missing_source_keys": missing_source_keys,
            "fail_safe": True,
        },
        "sources": sources,
    }