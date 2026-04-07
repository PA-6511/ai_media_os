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


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_RELEASE_READINESS_JSON_PATH = DEFAULT_REPORT_DIR / "release_readiness_latest.json"
DEFAULT_RELEASE_TREND_JSON_PATH = DEFAULT_REPORT_DIR / "release_readiness_trend_latest.json"
DEFAULT_ARTIFACT_INDEX_HTML_PATH = DEFAULT_REPORT_DIR / "artifact_index_latest.html"
DEFAULT_OPS_PORTAL_HTML_PATH = DEFAULT_REPORT_DIR / "ops_portal_latest.html"
DEFAULT_OPS_HOME_HTML_PATH = DEFAULT_REPORT_DIR / "ops_home_latest.html"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_read_json(path: Path | None) -> dict | None:
    if path is None or not path.exists() or not path.is_file():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    return payload if isinstance(payload, dict) else None


def _path_or_none(path: Path) -> str | None:
    if path.exists() and path.is_file():
        return str(path)
    return None


def _extract_daily_stats(payload: dict | None) -> dict[str, Any]:
    p = payload or {}
    return {
        "report_date": p.get("report_date"),
        "success_count": _to_int(p.get("success_count"), 0),
        "skipped_count": _to_int(p.get("skipped_count"), 0),
        "failed_count": _to_int(p.get("failed_count"), 0),
        "draft_count": _to_int(p.get("draft_count"), 0),
        "retry_queued_count": _to_int(p.get("retry_queued_count"), 0),
        "combined_count": _to_int(p.get("combined_count"), 0),
        "price_only_count": _to_int(p.get("price_only_count"), 0),
        "release_only_count": _to_int(p.get("release_only_count"), 0),
    }


def _extract_periodic_stats(payload: dict | None, period_key: str) -> dict[str, Any]:
    p = payload or {}
    return {
        period_key: p.get(period_key),
        "daily_report_count": _to_int(p.get("daily_report_count"), 0),
        "total_success_count": _to_int(p.get("total_success_count"), 0),
        "total_skipped_count": _to_int(p.get("total_skipped_count"), 0),
        "total_failed_count": _to_int(p.get("total_failed_count"), 0),
        "total_draft_count": _to_int(p.get("total_draft_count"), 0),
        "total_retry_queued_count": _to_int(p.get("total_retry_queued_count"), 0),
        "total_combined_count": _to_int(p.get("total_combined_count"), 0),
        "total_price_only_count": _to_int(p.get("total_price_only_count"), 0),
        "total_release_only_count": _to_int(p.get("total_release_only_count"), 0),
    }


def build_ops_summary() -> dict:
    """運用の最新状態を外部連携向けJSONに集約する。"""
    idx = build_artifact_index(report_dir=DEFAULT_REPORT_DIR, archive_dir=DEFAULT_ARCHIVE_DIR)

    daily_path = Path(str(idx.get("latest_daily_report_json"))) if idx.get("latest_daily_report_json") else None
    weekly_path = Path(str(idx.get("latest_weekly_report_json"))) if idx.get("latest_weekly_report_json") else None
    monthly_path = Path(str(idx.get("latest_monthly_report_json"))) if idx.get("latest_monthly_report_json") else None

    daily_payload = _safe_read_json(daily_path)
    weekly_payload = _safe_read_json(weekly_path)
    monthly_payload = _safe_read_json(monthly_path)
    release_payload = _safe_read_json(DEFAULT_RELEASE_READINESS_JSON_PATH)
    trend_payload = _safe_read_json(DEFAULT_RELEASE_TREND_JSON_PATH)

    latest_artifact_index = _path_or_none(DEFAULT_ARTIFACT_INDEX_HTML_PATH)
    latest_ops_portal = _path_or_none(DEFAULT_OPS_PORTAL_HTML_PATH)
    latest_ops_home = _path_or_none(DEFAULT_OPS_HOME_HTML_PATH)

    summary: dict[str, Any] = {
        "generated_at": _now_iso(),
        "latest_daily_report_json": idx.get("latest_daily_report_json"),
        "latest_weekly_report_json": idx.get("latest_weekly_report_json"),
        "latest_monthly_report_json": idx.get("latest_monthly_report_json"),
        "latest_dashboard": idx.get("latest_dashboard"),
        "latest_weekly_dashboard": idx.get("latest_weekly_dashboard"),
        "latest_monthly_dashboard": idx.get("latest_monthly_dashboard"),
        "latest_archive": idx.get("latest_archive"),
        "latest_artifact_index": latest_artifact_index,
        "latest_ops_portal": latest_ops_portal,
        "latest_ops_home": latest_ops_home,
        "latest_ops_decision_dashboard": idx.get("latest_ops_decision_dashboard"),
        "latest_release_readiness_json": idx.get("latest_release_readiness_json"),
        "latest_release_readiness_md": idx.get("latest_release_readiness_md"),
        "latest_release_readiness_trend_json": _path_or_none(DEFAULT_RELEASE_TREND_JSON_PATH),
        "latest_release_readiness_trend_md": str(DEFAULT_REPORT_DIR / "release_readiness_trend_latest.md")
        if (DEFAULT_REPORT_DIR / "release_readiness_trend_latest.md").exists()
        else None,
        "release_decision": (release_payload or {}).get("decision", "N/A"),
        "release_recommended_action": (release_payload or {}).get("recommended_action", "N/A"),
        "trend_total_days": _to_int((trend_payload or {}).get("total_days"), 0),
        "trend_release_count": _to_int((trend_payload or {}).get("release_count"), 0),
        "trend_review_count": _to_int((trend_payload or {}).get("review_count"), 0),
        "trend_hold_count": _to_int((trend_payload or {}).get("hold_count"), 0),
        "trend_latest_decision": (trend_payload or {}).get("latest_decision", "N/A"),
        "daily_stats": _extract_daily_stats(daily_payload),
        "weekly_stats": _extract_periodic_stats(weekly_payload, "report_week"),
        "monthly_stats": _extract_periodic_stats(monthly_payload, "report_month"),
        "counts": {
            "daily_report_count": _to_int(idx.get("daily_report_count"), 0),
            "weekly_report_count": _to_int(idx.get("weekly_report_count"), 0),
            "monthly_report_count": _to_int(idx.get("monthly_report_count"), 0),
            "archive_count": _to_int(idx.get("archive_count"), 0),
        },
    }

    return summary
