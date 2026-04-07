from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = BASE_DIR / "data" / "reports"
DEFAULT_DOCS_DIR = BASE_DIR / "docs"
SCHEMA_VERSION = "1.0"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _relative_if_exists(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None

    try:
        return str(path.relative_to(BASE_DIR)).replace("\\", "/")
    except ValueError:
        return str(path)


def build_ops_manifest() -> dict[str, Any]:
    status_light = _relative_if_exists(DEFAULT_REPORT_DIR / "ops_status_light_latest.json")
    ops_api_payload = _relative_if_exists(DEFAULT_REPORT_DIR / "ops_api_payload_latest.json")
    ops_summary = _relative_if_exists(DEFAULT_REPORT_DIR / "ops_summary_latest.json")
    artifact_index_html = _relative_if_exists(DEFAULT_REPORT_DIR / "artifact_index_latest.html")
    ops_portal_html = _relative_if_exists(DEFAULT_REPORT_DIR / "ops_portal_latest.html")
    ops_home_html = _relative_if_exists(DEFAULT_REPORT_DIR / "ops_home_latest.html")
    daily_dashboard_html = _relative_if_exists(DEFAULT_REPORT_DIR / "dashboard_latest.html")
    weekly_dashboard_html = _relative_if_exists(DEFAULT_REPORT_DIR / "weekly_dashboard_latest.html")
    monthly_dashboard_html = _relative_if_exists(DEFAULT_REPORT_DIR / "monthly_dashboard_latest.html")
    release_readiness_json = _relative_if_exists(DEFAULT_REPORT_DIR / "release_readiness_latest.json")
    status_badge_json = _relative_if_exists(DEFAULT_REPORT_DIR / "status_badge_latest.json")
    daily_checklist_md = _relative_if_exists(DEFAULT_DOCS_DIR / "daily_checklist_latest.md")
    runbook_md = _relative_if_exists(DEFAULT_DOCS_DIR / "runbook_latest.md")

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "status_light": status_light,
        "ops_api_payload": ops_api_payload,
        "ops_summary": ops_summary,
        "artifact_index_html": artifact_index_html,
        "ops_portal_html": ops_portal_html,
        "ops_home_html": ops_home_html,
        "daily_dashboard_html": daily_dashboard_html,
        "weekly_dashboard_html": weekly_dashboard_html,
        "monthly_dashboard_html": monthly_dashboard_html,
        "release_readiness_json": release_readiness_json,
        "status_badge_json": status_badge_json,
        "daily_checklist_md": daily_checklist_md,
        "runbook_md": runbook_md,
        "availability": {
            "status_light": status_light is not None,
            "ops_api_payload": ops_api_payload is not None,
            "ops_summary": ops_summary is not None,
            "artifact_index_html": artifact_index_html is not None,
            "ops_portal_html": ops_portal_html is not None,
            "ops_home_html": ops_home_html is not None,
            "daily_dashboard_html": daily_dashboard_html is not None,
            "weekly_dashboard_html": weekly_dashboard_html is not None,
            "monthly_dashboard_html": monthly_dashboard_html is not None,
            "release_readiness_json": release_readiness_json is not None,
            "status_badge_json": status_badge_json is not None,
            "daily_checklist_md": daily_checklist_md is not None,
            "runbook_md": runbook_md is not None,
        },
    }
