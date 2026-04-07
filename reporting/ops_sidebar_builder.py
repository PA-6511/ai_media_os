from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = BASE_DIR / "data" / "reports"
DEFAULT_NAVIGATION_PATH = DEFAULT_REPORT_DIR / "ops_navigation_latest.json"
DEFAULT_MANIFEST_PATH = DEFAULT_REPORT_DIR / "ops_manifest_latest.json"
DEFAULT_STATUS_LIGHT_PATH = DEFAULT_REPORT_DIR / "ops_status_light_latest.json"
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


def _to_rel_path(value: Any) -> str | None:
    if not value:
        return None

    text = str(value).strip()
    if not text:
        return None

    p = Path(text)
    if p.is_absolute():
        try:
            return str(p.relative_to(BASE_DIR)).replace("\\", "/")
        except ValueError:
            return str(p)

    return text.replace("\\", "/")


def _default_icon_for_key(key: str) -> str:
    k = key.lower()
    if "home" in k:
        return "home"
    if "portal" in k:
        return "compass"
    if "dashboard" in k:
        return "chart"
    if "status" in k or "decision" in k:
        return "pulse"
    if "summary" in k or "payload" in k:
        return "database"
    if "checklist" in k:
        return "check-square"
    if "runbook" in k:
        return "book"
    if "archive" in k:
        return "archive"
    return "file"


def _normalize_item(item: dict[str, Any]) -> dict[str, Any]:
    key = str(item.get("key") or item.get("id") or item.get("label") or "item").strip().lower().replace(" ", "_")
    label = str(item.get("label") or item.get("title") or key).strip()
    path = _to_rel_path(item.get("path") or item.get("href") or item.get("url"))
    icon = str(item.get("icon") or _default_icon_for_key(key)).strip()

    return {
        "key": key,
        "label": label,
        "path": path,
        "icon": icon,
    }


def _normalize_section(section: dict[str, Any], idx: int) -> dict[str, Any]:
    key = str(section.get("key") or section.get("id") or f"section_{idx}").strip().lower().replace(" ", "_")
    title = str(section.get("title") or section.get("label") or key).strip()
    icon = str(section.get("icon") or _default_icon_for_key(key)).strip()
    default_open = bool(section.get("default_open", idx == 0))

    items_src = section.get("items") if isinstance(section.get("items"), list) else []
    items = [_normalize_item(it) for it in items_src if isinstance(it, dict)]

    return {
        "key": key,
        "title": title,
        "icon": icon,
        "default_open": default_open,
        "items": items,
    }


def _build_sections_from_navigation(navigation: dict[str, Any]) -> list[dict[str, Any]]:
    sections_src = navigation.get("sections")
    if not isinstance(sections_src, list):
        return []

    return [
        _normalize_section(section, idx)
        for idx, section in enumerate(sections_src)
        if isinstance(section, dict)
    ]


def _build_fallback_sections(manifest: dict[str, Any], status: dict[str, Any]) -> list[dict[str, Any]]:
    decision = str(status.get("decision") or "N/A")
    health = str(status.get("health_grade") or "N/A")

    return [
        {
            "key": "today",
            "title": "Today",
            "icon": "home",
            "default_open": True,
            "items": [
                {
                    "key": "ops_home",
                    "label": "Ops Home",
                    "path": _to_rel_path(manifest.get("ops_home_html")),
                    "icon": "home",
                },
                {
                    "key": "ops_portal",
                    "label": "Ops Portal",
                    "path": _to_rel_path(manifest.get("ops_portal_html")),
                    "icon": "compass",
                },
                {
                    "key": "status_light",
                    "label": f"Today's Decision ({decision})",
                    "path": _to_rel_path(manifest.get("status_light")),
                    "icon": "pulse",
                },
            ],
        },
        {
            "key": "dashboards",
            "title": "Dashboards",
            "icon": "chart",
            "default_open": True,
            "items": [
                {
                    "key": "daily_dashboard",
                    "label": f"Daily Dashboard (Health {health})",
                    "path": _to_rel_path(manifest.get("daily_dashboard_html")),
                    "icon": "chart",
                },
                {
                    "key": "weekly_dashboard",
                    "label": "Weekly Dashboard",
                    "path": _to_rel_path(manifest.get("weekly_dashboard_html")),
                    "icon": "chart",
                },
                {
                    "key": "monthly_dashboard",
                    "label": "Monthly Dashboard",
                    "path": _to_rel_path(manifest.get("monthly_dashboard_html")),
                    "icon": "chart",
                },
            ],
        },
        {
            "key": "artifacts",
            "title": "Artifacts",
            "icon": "database",
            "default_open": False,
            "items": [
                {
                    "key": "ops_summary",
                    "label": "Ops Summary JSON",
                    "path": _to_rel_path(manifest.get("ops_summary")),
                    "icon": "database",
                },
                {
                    "key": "ops_api_payload",
                    "label": "Ops API Payload JSON",
                    "path": _to_rel_path(manifest.get("ops_api_payload")),
                    "icon": "database",
                },
                {
                    "key": "release_readiness",
                    "label": "Release Readiness JSON",
                    "path": _to_rel_path(manifest.get("release_readiness_json")),
                    "icon": "pulse",
                },
                {
                    "key": "status_badge",
                    "label": "Status Badge JSON",
                    "path": _to_rel_path(manifest.get("status_badge_json")),
                    "icon": "tag",
                },
                {
                    "key": "artifact_index",
                    "label": "Artifact Index",
                    "path": _to_rel_path(manifest.get("artifact_index_html")),
                    "icon": "list",
                },
            ],
        },
        {
            "key": "docs",
            "title": "Docs",
            "icon": "book",
            "default_open": False,
            "items": [
                {
                    "key": "daily_checklist",
                    "label": "Daily Checklist",
                    "path": _to_rel_path(manifest.get("daily_checklist_md")),
                    "icon": "check-square",
                },
                {
                    "key": "runbook",
                    "label": "Runbook",
                    "path": _to_rel_path(manifest.get("runbook_md")),
                    "icon": "book",
                },
            ],
        },
    ]


def build_ops_sidebar() -> dict[str, Any]:
    navigation = _safe_read_json(DEFAULT_NAVIGATION_PATH) or {}
    manifest = _safe_read_json(DEFAULT_MANIFEST_PATH) or {}
    status = _safe_read_json(DEFAULT_STATUS_LIGHT_PATH) or {}

    sections = _build_sections_from_navigation(navigation)
    if not sections:
        sections = _build_fallback_sections(manifest, status)

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "sections": sections,
        "meta": {
            "source_navigation_exists": DEFAULT_NAVIGATION_PATH.exists(),
            "source_manifest_exists": DEFAULT_MANIFEST_PATH.exists(),
            "source_status_exists": DEFAULT_STATUS_LIGHT_PATH.exists(),
        },
    }
