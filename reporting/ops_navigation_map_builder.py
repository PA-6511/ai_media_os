from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import BASE_DIR, DEFAULT_REPORT_DIR


DEFAULT_SIDEBAR_PATH = DEFAULT_REPORT_DIR / "ops_sidebar_latest.json"
DEFAULT_TABS_PATH = DEFAULT_REPORT_DIR / "ops_tabs_latest.json"
DEFAULT_LAYOUT_PATH = DEFAULT_REPORT_DIR / "ops_layout_latest.json"
DEFAULT_GUI_SCHEMA_PATH = DEFAULT_REPORT_DIR / "ops_gui_schema_latest.json"
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


def _slug(value: str) -> str:
    raw = str(value or "").strip().lower().replace("_", "-").replace(" ", "-")
    out = "".join(ch for ch in raw if ch.isalnum() or ch == "-")
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-") or "page"


def _path_basename(path_value: str) -> str:
    raw = str(path_value or "").strip()
    if not raw:
        return ""
    name = Path(raw).name
    for suffix in ("_latest.json", "_latest.html", "_latest.md", ".json", ".html", ".md"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _match_sidebar_to_tab(item_path: str, tab_related: dict[str, set[str]]) -> str | None:
    for tab_key, related in tab_related.items():
        if item_path in related:
            return tab_key
    return None


def build_ops_navigation_map() -> dict[str, Any]:
    sidebar = _safe_read_json(DEFAULT_SIDEBAR_PATH)
    tabs = _safe_read_json(DEFAULT_TABS_PATH)
    layout = _safe_read_json(DEFAULT_LAYOUT_PATH)
    schema = _safe_read_json(DEFAULT_GUI_SCHEMA_PATH)

    tab_rows = tabs.get("tabs") if isinstance(tabs.get("tabs"), list) else []
    sidebar_sections = sidebar.get("sections") if isinstance(sidebar.get("sections"), list) else []

    tab_related: dict[str, set[str]] = {}
    pages_index: dict[str, dict[str, Any]] = {}

    for tab in tab_rows:
        if not isinstance(tab, dict):
            continue
        tab_key = str(tab.get("key") or "")
        if not tab_key:
            continue

        primary_path = str(tab.get("primary_path") or "")
        related_paths = tab.get("related_paths") if isinstance(tab.get("related_paths"), list) else []
        related_set = {str(v) for v in related_paths if isinstance(v, str)}
        if primary_path:
            related_set.add(primary_path)
        tab_related[tab_key] = related_set

        pages_index[tab_key] = {
            "key": tab_key,
            "label": str(tab.get("title") or tab_key.title()),
            "route": f"/{_slug(tab_key)}",
            "parent": None,
            "children": [],
            "primary_source": primary_path or "N/A",
            "source": primary_path or "N/A",
            "type": "tab",
            "default": bool(tab.get("default")),
        }

    for section in sidebar_sections:
        if not isinstance(section, dict):
            continue
        section_key = str(section.get("key") or "")
        items = section.get("items") if isinstance(section.get("items"), list) else []

        for item in items:
            if not isinstance(item, dict):
                continue
            item_key = str(item.get("key") or "")
            label = str(item.get("label") or item_key or "")
            path_value = str(item.get("path") or "")
            if not item_key:
                continue

            parent = _match_sidebar_to_tab(path_value, tab_related)
            if parent is None:
                if section_key in {"dashboards"}:
                    parent = "dashboards" if "dashboards" in pages_index else None
                elif section_key in {"docs"}:
                    parent = "docs" if "docs" in pages_index else None
                elif section_key in {"artifacts"}:
                    parent = "reports" if "reports" in pages_index else None
                elif section_key in {"today"}:
                    parent = "overview" if "overview" in pages_index else None

            child_key = f"{parent}.{item_key}" if parent else item_key
            child_route = f"/{_slug(parent)}/{_slug(item_key)}" if parent else f"/{_slug(item_key)}"

            pages_index[child_key] = {
                "key": child_key,
                "label": label,
                "route": child_route,
                "parent": parent,
                "children": [],
                "primary_source": path_value or "N/A",
                "source": path_value or "N/A",
                "type": "sidebar_item",
            }

            if parent and parent in pages_index:
                children = pages_index[parent].get("children")
                if isinstance(children, list):
                    children.append(child_key)

    # Deduplicate and sort parent children for stable output.
    for page in pages_index.values():
        children = page.get("children")
        if isinstance(children, list):
            seen: set[str] = set()
            deduped: list[str] = []
            for child in children:
                child_s = str(child)
                if child_s in seen:
                    continue
                seen.add(child_s)
                deduped.append(child_s)
            page["children"] = deduped

    pages = sorted(pages_index.values(), key=lambda row: (str(row.get("parent") or ""), str(row.get("route") or "")))

    gui_schema_obj = schema.get("gui") if isinstance(schema.get("gui"), dict) else {}
    layout_obj = layout.get("layout") if isinstance(layout.get("layout"), dict) else {}
    layout_main = layout_obj.get("main") if isinstance(layout_obj.get("main"), dict) else {}
    default_tab_key = str(gui_schema_obj.get("default_tab_key") or layout_main.get("default_view") or "overview")

    sources = {
        "sidebar": _source_meta(DEFAULT_SIDEBAR_PATH, sidebar),
        "tabs": _source_meta(DEFAULT_TABS_PATH, tabs),
        "layout": _source_meta(DEFAULT_LAYOUT_PATH, layout),
        "gui_schema": _source_meta(DEFAULT_GUI_SCHEMA_PATH, schema),
    }
    missing_source_keys = [key for key, meta in sources.items() if not bool(meta.get("exists"))]
    partial = any(not bool(meta.get("loaded")) for meta in sources.values())

    root_pages = [page for page in pages if page.get("parent") is None]

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "pages": pages,
        "navigation": {
            "default_page_key": default_tab_key,
            "root_page_keys": [str(page.get("key")) for page in root_pages],
        },
        "summary": {
            "page_count": len(pages),
            "root_count": len(root_pages),
            "leaf_count": sum(1 for page in pages if not page.get("children")),
        },
        "status": {
            "partial": partial,
            "ready": len(missing_source_keys) == 0,
            "missing_source_keys": missing_source_keys,
            "fail_safe": True,
        },
        "sources": sources,
    }
