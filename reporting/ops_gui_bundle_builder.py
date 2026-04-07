from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import BASE_DIR, DEFAULT_REPORT_DIR


DEFAULT_DOCS_DIR = BASE_DIR / "docs"
SCHEMA_VERSION = "1.0"

ASSET_DEFINITIONS: list[dict[str, Any]] = [
    {"key": "bootstrap", "path": DEFAULT_REPORT_DIR / "ops_bootstrap_latest.json", "kind": "json"},
    {"key": "home_payload", "path": DEFAULT_REPORT_DIR / "ops_home_payload_latest.json", "kind": "json"},
    {"key": "sidebar", "path": DEFAULT_REPORT_DIR / "ops_sidebar_latest.json", "kind": "json"},
    {"key": "tabs", "path": DEFAULT_REPORT_DIR / "ops_tabs_latest.json", "kind": "json"},
    {"key": "widgets", "path": DEFAULT_REPORT_DIR / "ops_widgets_latest.json", "kind": "json"},
    {"key": "layout", "path": DEFAULT_REPORT_DIR / "ops_layout_latest.json", "kind": "json"},
    {"key": "header", "path": DEFAULT_REPORT_DIR / "ops_header_latest.json", "kind": "json"},
    {"key": "gui_schema", "path": DEFAULT_REPORT_DIR / "ops_gui_schema_latest.json", "kind": "json"},
    {"key": "mock_api", "path": DEFAULT_REPORT_DIR / "mock_api_home_latest.json", "kind": "json"},
    {"key": "cards", "path": DEFAULT_REPORT_DIR / "ops_cards_latest.json", "kind": "json"},
    {"key": "manifest", "path": DEFAULT_REPORT_DIR / "ops_manifest_latest.json", "kind": "json"},
    {"key": "portal", "path": DEFAULT_REPORT_DIR / "ops_portal_latest.html", "kind": "html"},
    {"key": "home", "path": DEFAULT_REPORT_DIR / "ops_home_latest.html", "kind": "html"},
    {"key": "gui_preview", "path": DEFAULT_REPORT_DIR / "ops_gui_preview_latest.html", "kind": "html"},
    {"key": "checklist", "path": DEFAULT_DOCS_DIR / "daily_checklist_latest.md", "kind": "markdown"},
    {"key": "runbook", "path": DEFAULT_DOCS_DIR / "runbook_latest.md", "kind": "markdown"},
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_rel_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR)).replace("\\", "/")
    except ValueError:
        return str(path)


def _stat_payload(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {
            "path": _to_rel_path(path),
            "exists": False,
            "size_bytes": None,
            "updated_at": None,
        }

    stat = path.stat()
    return {
        "path": _to_rel_path(path),
        "exists": True,
        "size_bytes": stat.st_size,
        "updated_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }


def _group_assets() -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {
        "json": [],
        "html": [],
        "markdown": [],
    }

    for spec in ASSET_DEFINITIONS:
        key = str(spec["key"])
        kind = str(spec["kind"])
        path = spec["path"]
        if not isinstance(path, Path):
            continue

        meta = _stat_payload(path)
        grouped[kind].append(
            {
                "key": key,
                **meta,
            }
        )

    return grouped


def _entrypoint_path_by_key(assets: list[dict[str, Any]], key: str) -> str:
    for asset in assets:
        if str(asset.get("key")) != key:
            continue
        if asset.get("exists"):
            return str(asset.get("path"))
        return "N/A"
    return "N/A"


def build_ops_gui_bundle_manifest() -> dict[str, Any]:
    grouped = _group_assets()

    json_assets = grouped["json"]
    html_assets = grouped["html"]
    markdown_assets = grouped["markdown"]

    all_assets = json_assets + html_assets + markdown_assets
    missing_keys = [str(asset.get("key")) for asset in all_assets if not asset.get("exists")]

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "json_assets": json_assets,
        "html_assets": html_assets,
        "markdown_assets": markdown_assets,
        "entrypoints": {
            "bootstrap": _entrypoint_path_by_key(json_assets, "bootstrap"),
            "home_payload": _entrypoint_path_by_key(json_assets, "home_payload"),
            "mock_api": _entrypoint_path_by_key(json_assets, "mock_api"),
            "preview_html": _entrypoint_path_by_key(html_assets, "gui_preview"),
        },
        "summary": {
            "json_count": len(json_assets),
            "html_count": len(html_assets),
            "markdown_count": len(markdown_assets),
            "total_assets": len(all_assets),
            "missing_count": len(missing_keys),
        },
        "status": {
            "ready": len(missing_keys) == 0,
            "missing_keys": missing_keys,
            "fail_safe": True,
        },
    }