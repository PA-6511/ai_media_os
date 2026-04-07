from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import BASE_DIR, DEFAULT_REPORT_DIR


DEFAULT_HEADER_JSON_PATH = DEFAULT_REPORT_DIR / "ops_header_latest.json"
DEFAULT_SIDEBAR_JSON_PATH = DEFAULT_REPORT_DIR / "ops_sidebar_latest.json"
DEFAULT_TABS_JSON_PATH = DEFAULT_REPORT_DIR / "ops_tabs_latest.json"
DEFAULT_CARDS_JSON_PATH = DEFAULT_REPORT_DIR / "ops_cards_latest.json"
DEFAULT_HOME_PAYLOAD_JSON_PATH = DEFAULT_REPORT_DIR / "ops_home_payload_latest.json"
DEFAULT_BOOTSTRAP_JSON_PATH = DEFAULT_REPORT_DIR / "ops_bootstrap_latest.json"
API_VERSION = "v1"


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


def _normalize_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR)).replace("\\", "/")
    except ValueError:
        return str(path)


def _generated_at(payload: dict[str, Any]) -> str | None:
    value = payload.get("generated_at")
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _source_info(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": _normalize_path(path),
        "exists": path.exists() and path.is_file(),
        "loaded": bool(payload),
        "generated_at": _generated_at(payload),
    }


def _list_count(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _missing_source_keys(sources: dict[str, dict[str, Any]]) -> list[str]:
    return [key for key, info in sources.items() if not info.get("exists")]


def _resource_endpoints() -> dict[str, dict[str, str]]:
    return {
        "home": {
            "path": "/api/home",
            "method": "GET",
        },
        "header": {
            "path": "/api/home/header",
            "method": "GET",
        },
        "sidebar": {
            "path": "/api/home/sidebar",
            "method": "GET",
        },
        "tabs": {
            "path": "/api/home/tabs",
            "method": "GET",
        },
        "cards": {
            "path": "/api/home/cards",
            "method": "GET",
        },
        "bootstrap": {
            "path": "/api/home/bootstrap",
            "method": "GET",
        },
    }


def build_mock_api_home() -> dict[str, Any]:
    header = _safe_read_json(DEFAULT_HEADER_JSON_PATH)
    sidebar = _safe_read_json(DEFAULT_SIDEBAR_JSON_PATH)
    tabs = _safe_read_json(DEFAULT_TABS_JSON_PATH)
    cards = _safe_read_json(DEFAULT_CARDS_JSON_PATH)
    home_payload = _safe_read_json(DEFAULT_HOME_PAYLOAD_JSON_PATH)
    bootstrap = _safe_read_json(DEFAULT_BOOTSTRAP_JSON_PATH)

    sources = {
        "header": _source_info(DEFAULT_HEADER_JSON_PATH, header),
        "sidebar": _source_info(DEFAULT_SIDEBAR_JSON_PATH, sidebar),
        "tabs": _source_info(DEFAULT_TABS_JSON_PATH, tabs),
        "cards": _source_info(DEFAULT_CARDS_JSON_PATH, cards),
        "home_payload": _source_info(DEFAULT_HOME_PAYLOAD_JSON_PATH, home_payload),
        "bootstrap": _source_info(DEFAULT_BOOTSTRAP_JSON_PATH, bootstrap),
    }
    missing_source_keys = _missing_source_keys(sources)
    endpoints = _resource_endpoints()

    return {
        "ok": True,
        "generated_at": _now_iso(),
        "api_version": API_VERSION,
        "endpoint": endpoints["home"],
        "data": {
            "header": header,
            "sidebar": sidebar,
            "tabs": tabs,
            "cards": cards,
            "home": home_payload,
            "bootstrap": bootstrap,
        },
        "endpoints": endpoints,
        "meta": {
            "counts": {
                "sidebar_sections": _list_count(sidebar.get("sections")),
                "tabs": _list_count(tabs.get("tabs")),
                "cards": _list_count(cards.get("cards")),
            },
            "sources": sources,
        },
        "status": {
            "partial": len(missing_source_keys) > 0,
            "missing_source_keys": missing_source_keys,
            "fail_safe": True,
        },
    }