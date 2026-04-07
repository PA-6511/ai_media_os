from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import DEFAULT_REPORT_DIR


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_HEADER_JSON_PATH = DEFAULT_REPORT_DIR / "ops_header_latest.json"
DEFAULT_SIDEBAR_JSON_PATH = DEFAULT_REPORT_DIR / "ops_sidebar_latest.json"
DEFAULT_TABS_JSON_PATH = DEFAULT_REPORT_DIR / "ops_tabs_latest.json"
DEFAULT_WIDGETS_JSON_PATH = DEFAULT_REPORT_DIR / "ops_widgets_latest.json"
DEFAULT_HOME_PAYLOAD_JSON_PATH = DEFAULT_REPORT_DIR / "ops_home_payload_latest.json"
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


def _normalize_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR)).replace("\\", "/")
    except ValueError:
        return str(path)


def _exists(path: Path) -> bool:
    return path.exists() and path.is_file()


def _extract_widget_keys(widgets_payload: dict[str, Any]) -> list[str]:
    widgets = widgets_payload.get("widgets")
    if not isinstance(widgets, list):
        return []

    keys: list[str] = []
    for widget in widgets:
        if not isinstance(widget, dict):
            continue
        key = str(widget.get("key") or "").strip()
        if key:
            keys.append(key)
    return keys


def build_ops_layout() -> dict[str, Any]:
    header = _safe_read_json(DEFAULT_HEADER_JSON_PATH) or {}
    sidebar = _safe_read_json(DEFAULT_SIDEBAR_JSON_PATH) or {}
    tabs = _safe_read_json(DEFAULT_TABS_JSON_PATH) or {}
    widgets = _safe_read_json(DEFAULT_WIDGETS_JSON_PATH) or {}
    home_payload = _safe_read_json(DEFAULT_HOME_PAYLOAD_JSON_PATH) or {}

    widget_keys = _extract_widget_keys(widgets)

    header_source = _normalize_path(DEFAULT_HEADER_JSON_PATH)
    sidebar_source = _normalize_path(DEFAULT_SIDEBAR_JSON_PATH)
    tabs_source = _normalize_path(DEFAULT_TABS_JSON_PATH)
    widgets_source = _normalize_path(DEFAULT_WIDGETS_JSON_PATH)
    home_payload_source = _normalize_path(DEFAULT_HOME_PAYLOAD_JSON_PATH)

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "layout": {
            "header": {
                "source": header_source,
                "visible": True,
                "sticky": True,
            },
            "sidebar": {
                "source": sidebar_source,
                "visible": True,
                "collapsible": True,
                "default_open": True,
            },
            "tabs": {
                "source": tabs_source,
                "visible": True,
                "placement": "top",
            },
            "main": {
                "widgets_source": widgets_source,
                "widget_order": widget_keys,
                "default_view": "overview",
                "supports_lazy_load": True,
            },
            "footer": {
                "source": home_payload_source,
                "visible": True,
                "source_selector": {
                    "path": "summary",
                },
            },
        },
        "responsive": {
            "desktop": {
                "sidebar_mode": "expanded",
                "tabs_mode": "horizontal",
                "main_columns": 2,
            },
            "tablet": {
                "sidebar_mode": "collapsible",
                "tabs_mode": "horizontal",
                "main_columns": 1,
            },
            "mobile": {
                "sidebar_mode": "drawer",
                "tabs_mode": "scrollable",
                "main_columns": 1,
            },
        },
        "summary": {
            "widget_count": len(widget_keys),
            "header_exists": bool(header),
            "sidebar_exists": bool(sidebar),
            "tabs_exists": bool(tabs),
            "widgets_exists": bool(widgets),
            "home_payload_exists": bool(home_payload),
        },
        "sources": {
            "header": {
                "path": header_source,
                "exists": _exists(DEFAULT_HEADER_JSON_PATH),
            },
            "sidebar": {
                "path": sidebar_source,
                "exists": _exists(DEFAULT_SIDEBAR_JSON_PATH),
            },
            "tabs": {
                "path": tabs_source,
                "exists": _exists(DEFAULT_TABS_JSON_PATH),
            },
            "widgets": {
                "path": widgets_source,
                "exists": _exists(DEFAULT_WIDGETS_JSON_PATH),
            },
            "home_payload": {
                "path": home_payload_source,
                "exists": _exists(DEFAULT_HOME_PAYLOAD_JSON_PATH),
            },
        },
    }