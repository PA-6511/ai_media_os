from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = BASE_DIR / "data" / "reports"
DEFAULT_MANIFEST_PATH = DEFAULT_REPORT_DIR / "ops_manifest_latest.json"


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


def _resolve_from_manifest(path_value: Any) -> tuple[str | None, Path | None]:
    if not path_value:
        return None, None

    raw = str(path_value).strip()
    if not raw:
        return None, None

    p = Path(raw)
    if p.is_absolute():
        normalized = raw
        return normalized, p

    normalized = raw.replace("\\", "/")
    return normalized, BASE_DIR / normalized


def _file_updated_at(path_obj: Path | None) -> str | None:
    if path_obj is None or not path_obj.exists() or not path_obj.is_file():
        return None

    try:
        return datetime.fromtimestamp(path_obj.stat().st_mtime, tz=timezone.utc).isoformat()
    except OSError:
        return None


def _entry(name: str, path_value: Any) -> dict[str, Any]:
    normalized, resolved = _resolve_from_manifest(path_value)
    updated_at = _file_updated_at(resolved)
    return {
        "name": name,
        "path": normalized,
        "updated_at": updated_at,
    }


def build_ops_timestamps() -> dict[str, Any]:
    manifest = _safe_read_json(DEFAULT_MANIFEST_PATH) or {}

    timestamps: list[dict[str, Any]] = [
        _entry("status_light", manifest.get("status_light")),
        _entry("ops_api_payload", manifest.get("ops_api_payload")),
        _entry("ops_summary", manifest.get("ops_summary")),
        _entry("artifact_index_html", manifest.get("artifact_index_html")),
        _entry("ops_portal_html", manifest.get("ops_portal_html")),
        _entry("ops_home_html", manifest.get("ops_home_html")),
        _entry("daily_dashboard_html", manifest.get("daily_dashboard_html")),
        _entry("weekly_dashboard_html", manifest.get("weekly_dashboard_html")),
        _entry("monthly_dashboard_html", manifest.get("monthly_dashboard_html")),
        _entry("release_readiness_json", manifest.get("release_readiness_json")),
        _entry("status_badge_json", manifest.get("status_badge_json")),
        _entry("daily_checklist_md", manifest.get("daily_checklist_md")),
        _entry("runbook_md", manifest.get("runbook_md")),
    ]

    # status_light から最新レポート/アーカイブも拾って GUI の更新状況表示に活用する。
    status_light_path = manifest.get("status_light")
    _, status_light_resolved = _resolve_from_manifest(status_light_path)
    status_light_payload = _safe_read_json(status_light_resolved) or {}

    timestamps.append(_entry("latest_daily_report", status_light_payload.get("latest_daily_report")))
    timestamps.append(_entry("latest_archive", status_light_payload.get("latest_archive")))

    return {
        "generated_at": _now_iso(),
        "timestamps": timestamps,
    }
