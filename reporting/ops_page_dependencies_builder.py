from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import BASE_DIR, DEFAULT_REPORT_DIR


DEFAULT_BOOTSTRAP_PATH = DEFAULT_REPORT_DIR / "ops_bootstrap_latest.json"
DEFAULT_GUI_SCHEMA_PATH = DEFAULT_REPORT_DIR / "ops_gui_schema_latest.json"
DEFAULT_WIDGETS_PATH = DEFAULT_REPORT_DIR / "ops_widgets_latest.json"
DEFAULT_LAYOUT_PATH = DEFAULT_REPORT_DIR / "ops_layout_latest.json"
DEFAULT_MOCK_API_PATH = DEFAULT_REPORT_DIR / "mock_api_home_latest.json"
DEFAULT_PREVIEW_PATH = DEFAULT_REPORT_DIR / "ops_gui_preview_latest.html"
DEFAULT_NAVIGATION_MAP_PATH = DEFAULT_REPORT_DIR / "ops_navigation_map_latest.json"
DEFAULT_GUI_HEALTH_PATH = DEFAULT_REPORT_DIR / "ops_gui_health_latest.json"
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


def _source_meta(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    updated_at = None
    if path.exists() and path.is_file():
        updated_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    return {
        "path": _normalize_path(path),
        "exists": path.exists() and path.is_file(),
        "loaded": bool(payload),
        "updated_at": updated_at,
    }


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _string(value: Any) -> str:
    return str(value or "").strip()


def _build_global_required(layout_payload: dict[str, Any]) -> list[str]:
    layout = layout_payload.get("layout") if isinstance(layout_payload.get("layout"), dict) else {}
    header = layout.get("header") if isinstance(layout.get("header"), dict) else {}
    sidebar = layout.get("sidebar") if isinstance(layout.get("sidebar"), dict) else {}
    tabs = layout.get("tabs") if isinstance(layout.get("tabs"), dict) else {}
    main = layout.get("main") if isinstance(layout.get("main"), dict) else {}

    return _dedupe_keep_order(
        [
            _normalize_path(DEFAULT_BOOTSTRAP_PATH),
            _normalize_path(DEFAULT_GUI_SCHEMA_PATH),
            _string(header.get("source")),
            _string(sidebar.get("source")),
            _string(tabs.get("source")),
            _string(main.get("widgets_source")),
        ]
    )


def build_ops_page_dependencies() -> dict[str, Any]:
    bootstrap = _safe_read_json(DEFAULT_BOOTSTRAP_PATH)
    schema = _safe_read_json(DEFAULT_GUI_SCHEMA_PATH)
    widgets = _safe_read_json(DEFAULT_WIDGETS_PATH)
    layout = _safe_read_json(DEFAULT_LAYOUT_PATH)
    navigation_map = _safe_read_json(DEFAULT_NAVIGATION_MAP_PATH)
    mock_api = _safe_read_json(DEFAULT_MOCK_API_PATH)
    gui_health = _safe_read_json(DEFAULT_GUI_HEALTH_PATH)

    pages = navigation_map.get("pages") if isinstance(navigation_map.get("pages"), list) else []
    widget_rows = widgets.get("widgets") if isinstance(widgets.get("widgets"), list) else []

    widget_sources = _dedupe_keep_order(
        [
            _string(row.get("source"))
            for row in widget_rows
            if isinstance(row, dict)
        ]
    )

    global_required = _build_global_required(layout)
    global_optional = _dedupe_keep_order(
        [
            _normalize_path(DEFAULT_MOCK_API_PATH),
            _normalize_path(DEFAULT_GUI_HEALTH_PATH),
            *widget_sources,
        ]
    )
    global_preview = _dedupe_keep_order(
        [
            _normalize_path(DEFAULT_PREVIEW_PATH),
            "data/reports/ops_home_latest.html",
            "data/reports/ops_portal_latest.html",
        ]
    )

    page_dependencies: list[dict[str, Any]] = []
    for page in pages:
        if not isinstance(page, dict):
            continue

        page_key = _string(page.get("key"))
        page_type = _string(page.get("type"))
        primary_source = _string(page.get("primary_source"))

        required_sources = _dedupe_keep_order([
            *global_required,
            primary_source,
        ])

        optional_sources = list(global_optional)
        if page_type == "tab":
            optional_sources.extend([
                _normalize_path(DEFAULT_PREVIEW_PATH),
                _normalize_path(DEFAULT_MOCK_API_PATH),
            ])
        if page_type == "sidebar_item":
            optional_sources.extend([
                _normalize_path(DEFAULT_MOCK_API_PATH),
            ])
        if page_key.startswith("overview"):
            optional_sources.extend([
                "data/reports/ops_status_light_latest.json",
                "data/reports/ops_header_latest.json",
            ])
        if page_key.startswith("dashboards"):
            optional_sources.extend([
                "data/reports/dashboard_latest.html",
                "data/reports/weekly_dashboard_latest.html",
                "data/reports/monthly_dashboard_latest.html",
            ])
        if page_key.startswith("reports"):
            optional_sources.extend([
                "data/reports/ops_summary_latest.json",
                "data/reports/ops_api_payload_latest.json",
                "data/reports/release_readiness_latest.json",
            ])

        preview_sources = list(global_preview)
        if primary_source.endswith(".html"):
            preview_sources.append(primary_source)

        page_dependencies.append(
            {
                "page_key": page_key,
                "route": _string(page.get("route")),
                "page_type": page_type,
                "required_sources": _dedupe_keep_order(required_sources),
                "optional_sources": _dedupe_keep_order(optional_sources),
                "preview_sources": _dedupe_keep_order(preview_sources),
            }
        )

    sources = {
        "bootstrap": _source_meta(DEFAULT_BOOTSTRAP_PATH, bootstrap),
        "gui_schema": _source_meta(DEFAULT_GUI_SCHEMA_PATH, schema),
        "widgets": _source_meta(DEFAULT_WIDGETS_PATH, widgets),
        "layout": _source_meta(DEFAULT_LAYOUT_PATH, layout),
        "navigation_map": _source_meta(DEFAULT_NAVIGATION_MAP_PATH, navigation_map),
        "mock_api": _source_meta(DEFAULT_MOCK_API_PATH, mock_api),
        "gui_health": _source_meta(DEFAULT_GUI_HEALTH_PATH, gui_health),
    }
    missing_source_keys = [key for key, meta in sources.items() if not bool(meta.get("exists"))]
    partial = any(not bool(meta.get("loaded")) for meta in sources.values())

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "pages": page_dependencies,
        "summary": {
            "page_count": len(page_dependencies),
            "required_source_total": sum(len(page.get("required_sources", [])) for page in page_dependencies),
            "optional_source_total": sum(len(page.get("optional_sources", [])) for page in page_dependencies),
            "preview_source_total": sum(len(page.get("preview_sources", [])) for page in page_dependencies),
        },
        "status": {
            "partial": partial,
            "ready": len(missing_source_keys) == 0,
            "missing_source_keys": missing_source_keys,
            "fail_safe": True,
        },
        "sources": sources,
    }
