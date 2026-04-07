from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import (
    DEFAULT_ARCHIVE_DIR,
    DEFAULT_REPORT_DIR,
    build_artifact_index,
)


DEFAULT_OPS_SUMMARY_JSON_PATH = DEFAULT_REPORT_DIR / "ops_summary_latest.json"
DEFAULT_RELEASE_READINESS_JSON_PATH = DEFAULT_REPORT_DIR / "release_readiness_latest.json"
DEFAULT_STATUS_BADGE_JSON_PATH = DEFAULT_REPORT_DIR / "status_badge_latest.json"
DEFAULT_ARTIFACT_INDEX_HTML_PATH = DEFAULT_REPORT_DIR / "artifact_index_latest.html"
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


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool_path_exists(path_str: Any) -> bool:
    return bool(path_str) and Path(str(path_str)).exists()


def build_ops_api_payload() -> dict[str, Any]:
    ops_summary = _safe_read_json(DEFAULT_OPS_SUMMARY_JSON_PATH) or {}
    release_readiness = _safe_read_json(DEFAULT_RELEASE_READINESS_JSON_PATH) or {}
    status_badge = _safe_read_json(DEFAULT_STATUS_BADGE_JSON_PATH) or {}
    artifact_index = build_artifact_index(
        report_dir=DEFAULT_REPORT_DIR,
        archive_dir=DEFAULT_ARCHIVE_DIR,
    )

    compact_summary = {
        "badge_text": _str_or_na(status_badge.get("badge_text")),
        "badge_level": _str_or_na(status_badge.get("badge_level")),
        "decision": _str_or_na(status_badge.get("decision") or release_readiness.get("decision") or ops_summary.get("release_decision")),
        "health_score": _int_or_none(status_badge.get("health_score") if status_badge else release_readiness.get("health_score")),
        "health_grade": _str_or_na(status_badge.get("health_grade") or release_readiness.get("health_grade")),
        "anomaly_overall": _str_or_na(status_badge.get("anomaly_overall") or release_readiness.get("anomaly_overall")),
        "recommended_action": _str_or_na(release_readiness.get("recommended_action") or ops_summary.get("release_recommended_action")),
        "trend_latest_decision": _str_or_na(ops_summary.get("trend_latest_decision")),
    }

    links = {
        "artifact_index_html": str(DEFAULT_ARTIFACT_INDEX_HTML_PATH) if DEFAULT_ARTIFACT_INDEX_HTML_PATH.exists() else None,
        "ops_portal_html": ops_summary.get("latest_ops_portal"),
        "ops_home_html": ops_summary.get("latest_ops_home"),
        "ops_decision_dashboard_html": ops_summary.get("latest_ops_decision_dashboard") or artifact_index.get("latest_ops_decision_dashboard"),
        "release_readiness_json": ops_summary.get("latest_release_readiness_json") or str(DEFAULT_RELEASE_READINESS_JSON_PATH),
        "status_badge_json": str(DEFAULT_STATUS_BADGE_JSON_PATH) if DEFAULT_STATUS_BADGE_JSON_PATH.exists() else None,
    }

    availability = {
        "ops_summary": bool(ops_summary),
        "release_readiness": bool(release_readiness),
        "status_badge": bool(status_badge),
        "artifact_index_html": _bool_path_exists(links.get("artifact_index_html")),
        "ops_portal_html": _bool_path_exists(links.get("ops_portal_html")),
        "ops_home_html": _bool_path_exists(links.get("ops_home_html")),
        "ops_decision_dashboard_html": _bool_path_exists(links.get("ops_decision_dashboard_html")),
    }

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "compact_summary": compact_summary,
        "status_badge": status_badge,
        "release_readiness": release_readiness,
        "ops_summary": ops_summary,
        "artifact_index": artifact_index,
        "links": links,
        "availability": availability,
    }