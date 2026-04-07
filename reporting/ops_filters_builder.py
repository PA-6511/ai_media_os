from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import BASE_DIR, DEFAULT_REPORT_DIR


DEFAULT_ALERT_CENTER_JSON_PATH = DEFAULT_REPORT_DIR / "ops_alert_center_latest.json"
DEFAULT_TIMELINE_JSON_PATH = DEFAULT_REPORT_DIR / "ops_timeline_latest.json"
DEFAULT_DECISION_SUMMARY_JSON_PATH = DEFAULT_REPORT_DIR / "ops_decision_summary_latest.json"
DEFAULT_RELEASE_READINESS_JSON_PATH = DEFAULT_REPORT_DIR / "release_readiness_latest.json"
DEFAULT_DAILY_REPORT_GLOB = "daily_report_*.json"
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


def _sorted_unique(values: list[str]) -> list[str]:
    return sorted({value for value in values if value})


def _extract_signal_modes() -> list[str]:
    values = ["normal", "price_only", "release_only", "combined"]

    daily_reports = [path for path in DEFAULT_REPORT_DIR.glob(DEFAULT_DAILY_REPORT_GLOB) if path.is_file()]
    latest = max(daily_reports, key=lambda p: (p.stat().st_mtime, p.name)) if daily_reports else None
    if latest:
        payload = _safe_read_json(latest)
        if int(payload.get("combined_count") or 0) > 0:
            values.append("combined")
        if int(payload.get("price_only_count") or 0) > 0:
            values.append("price_only")
        if int(payload.get("release_only_count") or 0) > 0:
            values.append("release_only")

    return _sorted_unique(values)


def build_ops_filters() -> dict[str, Any]:
    alert_center = _safe_read_json(DEFAULT_ALERT_CENTER_JSON_PATH)
    timeline = _safe_read_json(DEFAULT_TIMELINE_JSON_PATH)
    decision_summary = _safe_read_json(DEFAULT_DECISION_SUMMARY_JSON_PATH)
    release_readiness = _safe_read_json(DEFAULT_RELEASE_READINESS_JSON_PATH)

    severities = [
        str(alert.get("severity") or "").lower()
        for alert in (alert_center.get("alerts") if isinstance(alert_center.get("alerts"), list) else [])
        if isinstance(alert, dict)
    ]
    severities.extend(["info", "warning", "critical", "review"])

    statuses = [
        str(event.get("status") or "").upper()
        for event in (timeline.get("events") if isinstance(timeline.get("events"), list) else [])
        if isinstance(event, dict)
    ]
    statuses.extend(["PASS", "FAIL", "SKIP", "INFO", "OK"])

    categories = [
        str(event.get("category") or "")
        for event in (timeline.get("events") if isinstance(timeline.get("events"), list) else [])
        if isinstance(event, dict)
    ]

    decisions = [
        str(decision_summary.get("decision") or "").lower(),
        str((decision_summary.get("signals") or {}).get("readiness_decision") or "").lower(),
        str(release_readiness.get("decision") or "").lower(),
        "release",
        "review",
        "hold",
    ]

    date_range = ["today", "last_24h", "last_3d", "last_7d", "last_30d", "custom"]

    filters = {
        "severity": _sorted_unique(severities),
        "status": _sorted_unique(statuses),
        "category": _sorted_unique(categories),
        "decision": _sorted_unique(decisions),
        "signal_mode": _extract_signal_modes(),
        "date_range": date_range,
    }

    sources = {
        "alert_center": _source_meta(DEFAULT_ALERT_CENTER_JSON_PATH, alert_center),
        "timeline": _source_meta(DEFAULT_TIMELINE_JSON_PATH, timeline),
        "decision_summary": _source_meta(DEFAULT_DECISION_SUMMARY_JSON_PATH, decision_summary),
        "release_readiness": _source_meta(DEFAULT_RELEASE_READINESS_JSON_PATH, release_readiness),
    }
    missing_source_keys = [key for key, meta in sources.items() if not bool(meta.get("exists"))]
    partial = any(not bool(meta.get("loaded")) for meta in sources.values())

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "filters": filters,
        "summary": {
            "severity_count": len(filters["severity"]),
            "status_count": len(filters["status"]),
            "category_count": len(filters["category"]),
            "decision_count": len(filters["decision"]),
            "signal_mode_count": len(filters["signal_mode"]),
        },
        "status": {
            "partial": partial,
            "ready": len(missing_source_keys) == 0,
            "missing_source_keys": missing_source_keys,
            "fail_safe": True,
        },
        "sources": sources,
    }