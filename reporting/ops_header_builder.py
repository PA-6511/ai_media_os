from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import DEFAULT_REPORT_DIR


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_STATUS_BADGE_JSON_PATH = DEFAULT_REPORT_DIR / "status_badge_latest.json"
DEFAULT_STATUS_LIGHT_JSON_PATH = DEFAULT_REPORT_DIR / "ops_status_light_latest.json"
DEFAULT_OPS_TIMESTAMPS_JSON_PATH = DEFAULT_REPORT_DIR / "ops_timestamps_latest.json"
SCHEMA_VERSION = "1.0"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    return payload if isinstance(payload, dict) else None


def _str_or_na(value: Any) -> str:
    text = str(value).strip() if value is not None else ""
    return text if text else "N/A"


def _normalize_decision(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "N/A"
    return text.upper()


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _resolve_path(path_value: Any) -> Path | None:
    if path_value is None:
        return None

    raw = str(path_value).strip()
    if not raw:
        return None

    path_obj = Path(raw)
    if path_obj.is_absolute():
        return path_obj

    return BASE_DIR / raw.replace("\\", "/")


def _path_exists(path_value: Any) -> bool:
    path_obj = _resolve_path(path_value)
    return bool(path_obj and path_obj.exists() and path_obj.is_file())


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


def _max_iso(values: list[Any]) -> str:
    latest: datetime | None = None
    latest_text: str | None = None

    for value in values:
        dt = _parse_iso(value)
        if dt is None:
            continue
        if latest is None or dt > latest:
            latest = dt
            latest_text = dt.isoformat()

    return latest_text or "N/A"


def _timestamps_by_name(timestamps_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = timestamps_payload.get("timestamps")
    if not isinstance(rows, list):
        return {}

    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = str(row.get("name") or "").strip()
        if not key:
            continue
        result[key] = row
    return result


def build_ops_header() -> dict[str, Any]:
    status_badge = _safe_read_json(DEFAULT_STATUS_BADGE_JSON_PATH) or {}
    status_light = _safe_read_json(DEFAULT_STATUS_LIGHT_JSON_PATH) or {}
    ops_timestamps = _safe_read_json(DEFAULT_OPS_TIMESTAMPS_JSON_PATH) or {}

    ts_index = _timestamps_by_name(ops_timestamps)

    decision = _normalize_decision(status_light.get("decision") or status_badge.get("decision"))
    badge_text = _str_or_na(status_light.get("badge_text") or status_badge.get("badge_text"))

    health_score = _int_or_none(
        status_light.get("health_score")
        if status_light.get("health_score") is not None
        else status_badge.get("health_score")
    )

    health_grade = _str_or_na(status_light.get("health_grade") or status_badge.get("health_grade"))
    anomaly_overall = _str_or_na(status_light.get("anomaly_overall") or status_badge.get("anomaly_overall"))

    latest_archive_entry = ts_index.get("latest_archive", {})
    latest_archive_path = status_light.get("latest_archive") or latest_archive_entry.get("path")
    latest_archive_available = _path_exists(latest_archive_path)

    last_updated = _max_iso(
        [
            status_light.get("generated_at"),
            status_badge.get("generated_at"),
            ops_timestamps.get("generated_at"),
            (ts_index.get("status_light") or {}).get("updated_at"),
            (ts_index.get("status_badge_json") or {}).get("updated_at"),
            latest_archive_entry.get("updated_at"),
        ]
    )

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "decision": decision,
        "badge_text": badge_text,
        "health_score": health_score,
        "health_grade": health_grade,
        "anomaly_overall": anomaly_overall,
        "last_updated": last_updated,
        "latest_archive_available": latest_archive_available,
    }