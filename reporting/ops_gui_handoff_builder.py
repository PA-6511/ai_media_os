from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import BASE_DIR, DEFAULT_REPORT_DIR


DEFAULT_DOCS_DIR = BASE_DIR / "docs"
SCHEMA_VERSION = "1.0"

ASSET_DEFINITIONS: list[dict[str, Any]] = [
    {"key": "bootstrap", "path": DEFAULT_REPORT_DIR / "ops_bootstrap_latest.json", "kind": "json", "role": "entrypoint"},
    {"key": "home_payload", "path": DEFAULT_REPORT_DIR / "ops_home_payload_latest.json", "kind": "json", "role": "entrypoint"},
    {"key": "sidebar", "path": DEFAULT_REPORT_DIR / "ops_sidebar_latest.json", "kind": "json", "role": "module"},
    {"key": "tabs", "path": DEFAULT_REPORT_DIR / "ops_tabs_latest.json", "kind": "json", "role": "module"},
    {"key": "widgets", "path": DEFAULT_REPORT_DIR / "ops_widgets_latest.json", "kind": "json", "role": "module"},
    {"key": "layout", "path": DEFAULT_REPORT_DIR / "ops_layout_latest.json", "kind": "json", "role": "module"},
    {"key": "header", "path": DEFAULT_REPORT_DIR / "ops_header_latest.json", "kind": "json", "role": "module"},
    {"key": "gui_schema", "path": DEFAULT_REPORT_DIR / "ops_gui_schema_latest.json", "kind": "json", "role": "schema"},
    {"key": "mock_api", "path": DEFAULT_REPORT_DIR / "mock_api_home_latest.json", "kind": "json", "role": "api_mock"},
    {"key": "ops_manifest", "path": DEFAULT_REPORT_DIR / "ops_manifest_latest.json", "kind": "json", "role": "reference"},
    {"key": "bundle_manifest", "path": DEFAULT_REPORT_DIR / "ops_gui_bundle_manifest_latest.json", "kind": "json", "role": "reference"},
    {"key": "gui_preview", "path": DEFAULT_REPORT_DIR / "ops_gui_preview_latest.html", "kind": "html", "role": "preview"},
    {"key": "runbook", "path": DEFAULT_DOCS_DIR / "runbook_latest.md", "kind": "doc", "role": "doc"},
    {"key": "daily_checklist", "path": DEFAULT_DOCS_DIR / "daily_checklist_latest.md", "kind": "doc", "role": "doc"},
]

READ_ORDER_KEYS = [
    "bootstrap",
    "gui_schema",
    "mock_api",
    "home_payload",
    "sidebar",
    "tabs",
    "widgets",
    "layout",
    "header",
    "gui_preview",
    "bundle_manifest",
    "ops_manifest",
    "runbook",
    "daily_checklist",
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


def _collect_assets() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    assets: list[dict[str, Any]] = []
    assets_by_key: dict[str, dict[str, Any]] = {}

    for spec in ASSET_DEFINITIONS:
        key = str(spec.get("key") or "")
        kind = str(spec.get("kind") or "")
        role = str(spec.get("role") or "")
        path = spec.get("path")
        if not key or not kind or not isinstance(path, Path):
            continue

        payload = {
            "key": key,
            "kind": kind,
            "role": role,
            **_stat_payload(path),
        }
        assets.append(payload)
        assets_by_key[key] = payload

    return assets, assets_by_key


def _pick_path(assets_by_key: dict[str, dict[str, Any]], key: str) -> str:
    asset = assets_by_key.get(key)
    if not asset:
        return "N/A"
    if bool(asset.get("exists")):
        return str(asset.get("path"))
    return "N/A"


def _read_order(assets_by_key: dict[str, dict[str, Any]]) -> list[str]:
    paths: list[str] = []
    for key in READ_ORDER_KEYS:
        path = _pick_path(assets_by_key, key)
        if path != "N/A":
            paths.append(path)
    return paths


def _filter_assets(assets: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [asset for asset in assets if str(asset.get("kind")) == kind]


def build_ops_gui_handoff() -> dict[str, Any]:
    assets, assets_by_key = _collect_assets()

    json_assets = _filter_assets(assets, "json")
    html_assets = _filter_assets(assets, "html")
    docs = _filter_assets(assets, "doc")

    missing_keys = [str(asset.get("key")) for asset in assets if not bool(asset.get("exists"))]

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "read_order": _read_order(assets_by_key),
        "entrypoints": {
            "bootstrap": _pick_path(assets_by_key, "bootstrap"),
            "home_payload": _pick_path(assets_by_key, "home_payload"),
            "gui_schema": _pick_path(assets_by_key, "gui_schema"),
        },
        "preview": {
            "gui_preview_html": _pick_path(assets_by_key, "gui_preview"),
        },
        "api_mock": {
            "home": _pick_path(assets_by_key, "mock_api"),
        },
        "json_assets": json_assets,
        "html_assets": html_assets,
        "docs": docs,
        "summary": {
            "json_count": len(json_assets),
            "html_count": len(html_assets),
            "docs_count": len(docs),
            "total_assets": len(assets),
            "missing_count": len(missing_keys),
        },
        "status": {
            "ready": len(missing_keys) == 0,
            "missing_keys": missing_keys,
            "fail_safe": True,
        },
    }