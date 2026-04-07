from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import BASE_DIR, DEFAULT_REPORT_DIR


DEFAULT_STATUS_LIGHT_JSON_PATH = DEFAULT_REPORT_DIR / "ops_status_light_latest.json"
DEFAULT_ALERT_CENTER_JSON_PATH = DEFAULT_REPORT_DIR / "ops_alert_center_latest.json"
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


def _latest_matching(pattern: str) -> Path | None:
    candidates = [path for path in DEFAULT_REPORT_DIR.glob(pattern) if path.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: (path.stat().st_mtime, path.name))


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _source_meta(path: Path | None, payload: dict[str, Any]) -> dict[str, Any]:
    if path is None:
        return {
            "path": None,
            "exists": False,
            "loaded": False,
            "updated_at": None,
        }

    updated_at = None
    if path.exists() and path.is_file():
        updated_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()

    return {
        "path": _normalize_path(path),
        "exists": path.exists() and path.is_file(),
        "loaded": bool(payload),
        "updated_at": updated_at,
    }


def _kpi(key: str, label: str, value: Any, category: str) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "value": value,
        "category": category,
    }


def build_ops_kpi_summary() -> dict[str, Any]:
    daily_path = _latest_matching("daily_report_*.json")
    weekly_path = _latest_matching("weekly_report_*.json")
    monthly_path = _latest_matching("monthly_report_*.json")

    daily = _safe_read_json(daily_path) if daily_path else {}
    weekly = _safe_read_json(weekly_path) if weekly_path else {}
    monthly = _safe_read_json(monthly_path) if monthly_path else {}
    status_light = _safe_read_json(DEFAULT_STATUS_LIGHT_JSON_PATH)
    alert_center = _safe_read_json(DEFAULT_ALERT_CENTER_JSON_PATH)

    health_score = status_light.get("health_score")
    health_grade = status_light.get("health_grade")
    anomaly_overall = status_light.get("anomaly_overall") or "N/A"
    alert_count = _to_int((alert_center.get("summary") or {}).get("alert_count"), 0)

    kpis = [
        _kpi("success_count", "成功件数", _to_int(daily.get("success_count"), 0), "daily"),
        _kpi("skipped_count", "スキップ件数", _to_int(daily.get("skipped_count"), 0), "daily"),
        _kpi("failed_count", "失敗件数", _to_int(daily.get("failed_count"), 0), "daily"),
        _kpi("draft_count", "Draft件数", _to_int(daily.get("draft_count"), 0), "daily"),
        _kpi("retry_queued_count", "Retry Queue件数", _to_int(daily.get("retry_queued_count"), 0), "daily"),
        _kpi("health_score", "Health Score", health_score, "status"),
        _kpi("health_grade", "Health Grade", health_grade or "N/A", "status"),
        _kpi("anomaly_overall", "Anomaly Status", anomaly_overall, "status"),
        _kpi("alert_count", "Alert件数", alert_count, "status"),
        _kpi("weekly_total_success_count", "週次成功合計", _to_int(weekly.get("total_success_count"), 0), "weekly"),
        _kpi("weekly_total_failed_count", "週次失敗合計", _to_int(weekly.get("total_failed_count"), 0), "weekly"),
        _kpi("monthly_total_success_count", "月次成功合計", _to_int(monthly.get("total_success_count"), 0), "monthly"),
        _kpi("monthly_total_failed_count", "月次失敗合計", _to_int(monthly.get("total_failed_count"), 0), "monthly"),
    ]

    sources = {
        "daily_report": _source_meta(daily_path, daily),
        "weekly_report": _source_meta(weekly_path, weekly),
        "monthly_report": _source_meta(monthly_path, monthly),
        "status_light": _source_meta(DEFAULT_STATUS_LIGHT_JSON_PATH, status_light),
        "alert_center": _source_meta(DEFAULT_ALERT_CENTER_JSON_PATH, alert_center),
    }
    missing_source_keys = [key for key, meta in sources.items() if not bool(meta.get("exists"))]
    partial = any(not bool(meta.get("loaded")) for meta in sources.values())

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "kpis": kpis,
        "snapshots": {
            "daily": {
                "report_date": daily.get("report_date"),
                "success_count": _to_int(daily.get("success_count"), 0),
                "skipped_count": _to_int(daily.get("skipped_count"), 0),
                "failed_count": _to_int(daily.get("failed_count"), 0),
                "draft_count": _to_int(daily.get("draft_count"), 0),
                "retry_queued_count": _to_int(daily.get("retry_queued_count"), 0),
            },
            "weekly": {
                "report_week": weekly.get("report_week"),
                "total_success_count": _to_int(weekly.get("total_success_count"), 0),
                "total_failed_count": _to_int(weekly.get("total_failed_count"), 0),
            },
            "monthly": {
                "report_month": monthly.get("report_month"),
                "total_success_count": _to_int(monthly.get("total_success_count"), 0),
                "total_failed_count": _to_int(monthly.get("total_failed_count"), 0),
            },
            "status": {
                "health_score": health_score,
                "health_grade": health_grade or "N/A",
                "anomaly_overall": anomaly_overall,
                "alert_count": alert_count,
            },
        },
        "status": {
            "partial": partial,
            "ready": len(missing_source_keys) == 0,
            "missing_source_keys": missing_source_keys,
            "fail_safe": True,
        },
        "sources": sources,
    }