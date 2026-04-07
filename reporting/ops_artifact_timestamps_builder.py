from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = BASE_DIR / "data" / "reports"
DEFAULT_ARCHIVE_DIR = BASE_DIR / "data" / "archives"
DEFAULT_MANIFEST_PATH = DEFAULT_REPORT_DIR / "ops_manifest_latest.json"
DEFAULT_STATUS_LIGHT_PATH = DEFAULT_REPORT_DIR / "ops_status_light_latest.json"
SCHEMA_VERSION = "1.0"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _resolve_path(value: Any) -> Path | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    p = Path(raw)
    if p.is_absolute():
        return p
    return (BASE_DIR / raw).resolve()


def _entry(key: str, path_obj: Path | None) -> dict[str, Any]:
    exists = bool(path_obj and path_obj.exists() and path_obj.is_file())
    updated_at = None
    path_str = None

    if path_obj is not None:
        path_str = str(path_obj)
    if exists and path_obj is not None:
        try:
            updated_at = datetime.fromtimestamp(path_obj.stat().st_mtime, tz=timezone.utc).isoformat()
        except OSError:
            updated_at = None

    return {
        "key": key,
        "path": path_str,
        "updated_at": updated_at,
        "exists": exists,
    }


def _latest_file(directory: Path, pattern: str) -> Path | None:
    if not directory.exists() or not directory.is_dir():
        return None
    files = [p for p in directory.glob(pattern) if p.is_file()]
    if not files:
        return None
    return max(files, key=lambda p: (p.stat().st_mtime, p.name))


def build_ops_artifact_timestamps() -> dict[str, Any]:
    manifest = _safe_read_json(DEFAULT_MANIFEST_PATH)
    status_light = _safe_read_json(DEFAULT_STATUS_LIGHT_PATH)

    manifest_map: dict[str, Any] = {
        "status_light": manifest.get("status_light"),
        "ops_api_payload": manifest.get("ops_api_payload"),
        "ops_summary": manifest.get("ops_summary"),
        "artifact_index_html": manifest.get("artifact_index_html"),
        "ops_portal_html": manifest.get("ops_portal_html"),
        "ops_home_html": manifest.get("ops_home_html"),
        "dashboard_daily": manifest.get("daily_dashboard_html"),
        "dashboard_weekly": manifest.get("weekly_dashboard_html"),
        "dashboard_monthly": manifest.get("monthly_dashboard_html"),
        "release_readiness": manifest.get("release_readiness_json"),
        "status_badge": manifest.get("status_badge_json"),
        "daily_checklist": manifest.get("daily_checklist_md"),
        "runbook": manifest.get("runbook_md"),
    }

    core_map: dict[str, Path] = {
        "bootstrap": DEFAULT_REPORT_DIR / "ops_bootstrap_latest.json",
        "gui_schema": DEFAULT_REPORT_DIR / "ops_gui_schema_latest.json",
        "gui_handoff": DEFAULT_REPORT_DIR / "ops_gui_handoff_latest.json",
        "mock_api": DEFAULT_REPORT_DIR / "mock_api_home_latest.json",
        "navigation_search": DEFAULT_REPORT_DIR / "ops_nav_search_latest.json",
        "error_states": DEFAULT_REPORT_DIR / "ops_error_states_latest.json",
        "empty_states": DEFAULT_REPORT_DIR / "ops_empty_states_latest.json",
    }

    artifacts: list[dict[str, Any]] = []

    for key, value in manifest_map.items():
        artifacts.append(_entry(key, _resolve_path(value)))

    for key, path_obj in core_map.items():
        artifacts.append(_entry(key, path_obj.resolve()))

    latest_monthly = _latest_file(DEFAULT_REPORT_DIR, "monthly_report_*.json")
    artifacts.append(_entry("monthly_report", latest_monthly))

    latest_archive_from_status = _resolve_path(status_light.get("latest_archive"))
    latest_archive = latest_archive_from_status or _latest_file(DEFAULT_ARCHIVE_DIR, "ops_archive_*.zip")
    artifacts.append(_entry("archive", latest_archive))

    # Remove duplicates by key while keeping first occurrence.
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in artifacts:
        key = str(item.get("key") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    deduped.sort(key=lambda row: str(row.get("key") or ""))

    missing_keys = [str(item.get("key")) for item in deduped if not bool(item.get("exists"))]

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "artifacts": deduped,
        "summary": {
            "total": len(deduped),
            "exists_count": sum(1 for item in deduped if bool(item.get("exists"))),
            "missing_count": sum(1 for item in deduped if not bool(item.get("exists"))),
            "missing_keys": missing_keys,
        },
        "status": {
            "partial": any(not bool(item.get("exists")) for item in deduped),
            "ready": len(missing_keys) == 0,
            "fail_safe": True,
        },
        "sources": {
            "manifest": {
                "path": str(DEFAULT_MANIFEST_PATH),
                "exists": DEFAULT_MANIFEST_PATH.exists() and DEFAULT_MANIFEST_PATH.is_file(),
                "loaded": bool(manifest),
            },
            "status_light": {
                "path": str(DEFAULT_STATUS_LIGHT_PATH),
                "exists": DEFAULT_STATUS_LIGHT_PATH.exists() and DEFAULT_STATUS_LIGHT_PATH.is_file(),
                "loaded": bool(status_light),
            },
        },
    }
