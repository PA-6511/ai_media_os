from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import BASE_DIR, DEFAULT_REPORT_DIR


DEFAULT_SIDEBAR_JSON_PATH = DEFAULT_REPORT_DIR / "ops_sidebar_latest.json"
DEFAULT_TABS_JSON_PATH = DEFAULT_REPORT_DIR / "ops_tabs_latest.json"
DEFAULT_WIDGETS_JSON_PATH = DEFAULT_REPORT_DIR / "ops_widgets_latest.json"
DEFAULT_LAYOUT_JSON_PATH = DEFAULT_REPORT_DIR / "ops_layout_latest.json"
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


def _source_info(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": _normalize_path(path),
        "exists": path.exists() and path.is_file(),
        "loaded": bool(payload),
    }


def _get_sidebar_section_keys(sidebar: dict[str, Any]) -> list[str]:
    sections = sidebar.get("sections")
    if not isinstance(sections, list):
        return []

    keys: list[str] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        key = str(section.get("key") or "").strip()
        if key:
            keys.append(key)
    return keys


def _get_widget_order(layout: dict[str, Any], widgets: dict[str, Any]) -> list[str]:
    layout_widget_order = ((layout.get("layout") or {}).get("main") or {}).get("widget_order")
    if isinstance(layout_widget_order, list):
        ordered_keys = [str(value).strip() for value in layout_widget_order if str(value).strip()]
        if ordered_keys:
            return ordered_keys

    widgets_list = widgets.get("widgets")
    if not isinstance(widgets_list, list):
        return []

    ordered = sorted(
        [widget for widget in widgets_list if isinstance(widget, dict)],
        key=lambda widget: int(widget.get("order") or 0),
    )
    return [str(widget.get("key") or "").strip() for widget in ordered if str(widget.get("key") or "").strip()]


def _get_default_tab_key(tabs: dict[str, Any]) -> str | None:
    tabs_list = tabs.get("tabs")
    if not isinstance(tabs_list, list):
        return None

    for tab in tabs_list:
        if not isinstance(tab, dict):
            continue
        if tab.get("default"):
            key = str(tab.get("key") or "").strip()
            if key:
                return key

    for tab in tabs_list:
        if not isinstance(tab, dict):
            continue
        key = str(tab.get("key") or "").strip()
        if key:
            return key

    return None


def _widget_map(widgets: dict[str, Any]) -> dict[str, dict[str, Any]]:
    widgets_list = widgets.get("widgets")
    if not isinstance(widgets_list, list):
        return {}

    mapped: dict[str, dict[str, Any]] = {}
    for widget in widgets_list:
        if not isinstance(widget, dict):
            continue
        key = str(widget.get("key") or "").strip()
        if key:
            mapped[key] = widget
    return mapped


def _layout_regions(layout: dict[str, Any]) -> list[str]:
    layout_payload = layout.get("layout")
    if not isinstance(layout_payload, dict):
        return []
    return [key for key, value in layout_payload.items() if isinstance(value, dict)]


def _build_views(
    sidebar: dict[str, Any],
    tabs: dict[str, Any],
    widgets: dict[str, Any],
    layout: dict[str, Any],
) -> list[dict[str, Any]]:
    tabs_list = tabs.get("tabs") if isinstance(tabs.get("tabs"), list) else []
    widget_order = _get_widget_order(layout, widgets)
    widget_details = _widget_map(widgets)
    sidebar_section_keys = _get_sidebar_section_keys(sidebar)
    regions = _layout_regions(layout)

    views: list[dict[str, Any]] = []
    for index, tab in enumerate(tabs_list, start=1):
        if not isinstance(tab, dict):
            continue

        tab_key = str(tab.get("key") or f"tab_{index}").strip()
        tab_title = str(tab.get("title") or tab_key).strip()
        related_paths = tab.get("related_paths") if isinstance(tab.get("related_paths"), list) else []

        views.append(
            {
                "view_key": tab_key,
                "title": tab_title,
                "tab_key": tab_key,
                "default": bool(tab.get("default")),
                "primary_path": tab.get("primary_path"),
                "related_paths": related_paths,
                "layout_regions": regions,
                "sidebar_section_keys": sidebar_section_keys,
                "main_widget_keys": widget_order,
                "main_widgets": [widget_details[key] for key in widget_order if key in widget_details],
            }
        )

    if views:
        return views

    return [
        {
            "view_key": "overview",
            "title": "Overview",
            "tab_key": None,
            "default": True,
            "primary_path": None,
            "related_paths": [],
            "layout_regions": regions,
            "sidebar_section_keys": sidebar_section_keys,
            "main_widget_keys": widget_order,
            "main_widgets": [widget_details[key] for key in widget_order if key in widget_details],
        }
    ]


def _missing_source_keys(sources: dict[str, dict[str, Any]]) -> list[str]:
    return [key for key, info in sources.items() if not info.get("exists")]


def build_ops_gui_schema() -> dict[str, Any]:
    sidebar = _safe_read_json(DEFAULT_SIDEBAR_JSON_PATH)
    tabs = _safe_read_json(DEFAULT_TABS_JSON_PATH)
    widgets = _safe_read_json(DEFAULT_WIDGETS_JSON_PATH)
    layout = _safe_read_json(DEFAULT_LAYOUT_JSON_PATH)

    sources = {
        "sidebar": _source_info(DEFAULT_SIDEBAR_JSON_PATH, sidebar),
        "tabs": _source_info(DEFAULT_TABS_JSON_PATH, tabs),
        "widgets": _source_info(DEFAULT_WIDGETS_JSON_PATH, widgets),
        "layout": _source_info(DEFAULT_LAYOUT_JSON_PATH, layout),
    }
    views = _build_views(sidebar, tabs, widgets, layout)
    widget_order = _get_widget_order(layout, widgets)
    default_tab_key = _get_default_tab_key(tabs)
    missing_source_keys = _missing_source_keys(sources)

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "sidebar": sidebar,
        "tabs": tabs,
        "widgets": widgets,
        "layout": layout,
        "gui": {
            "default_tab_key": default_tab_key,
            "sidebar_section_keys": _get_sidebar_section_keys(sidebar),
            "tab_keys": [str(view.get("tab_key")) for view in views if view.get("tab_key")],
            "widget_order": widget_order,
            "views": views,
        },
        "summary": {
            "sidebar_section_count": len(_get_sidebar_section_keys(sidebar)),
            "tab_count": len(tabs.get("tabs") if isinstance(tabs.get("tabs"), list) else []),
            "widget_count": len(widgets.get("widgets") if isinstance(widgets.get("widgets"), list) else []),
            "layout_region_count": len(_layout_regions(layout)),
            "view_count": len(views),
            "missing_source_count": len(missing_source_keys),
        },
        "status": {
            "ready": len(missing_source_keys) == 0,
            "missing_source_keys": missing_source_keys,
            "fail_safe": True,
        },
        "sources": sources,
    }