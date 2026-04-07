from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import DEFAULT_REPORT_DIR


DEFAULT_MANIFEST_JSON_PATH = DEFAULT_REPORT_DIR / "ops_manifest_latest.json"
DEFAULT_HOME_PAYLOAD_JSON_PATH = DEFAULT_REPORT_DIR / "ops_home_payload_latest.json"
DEFAULT_SIDEBAR_JSON_PATH = DEFAULT_REPORT_DIR / "ops_sidebar_latest.json"
DEFAULT_TABS_JSON_PATH = DEFAULT_REPORT_DIR / "ops_tabs_latest.json"
DEFAULT_HEADER_JSON_PATH = DEFAULT_REPORT_DIR / "ops_header_latest.json"
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


def _extract_generated_at(payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None

    value = payload.get("generated_at")
    if value is None:
        return None

    text = str(value).strip()
    return text if text else None


def _extract_status(home_payload: dict[str, Any], header: dict[str, Any]) -> dict[str, Any]:
    status = home_payload.get("status")
    if isinstance(status, dict):
        return status

    return {
        "decision": header.get("decision", "N/A"),
        "badge_text": header.get("badge_text", "N/A"),
        "health_score": header.get("health_score"),
        "health_grade": header.get("health_grade", "N/A"),
        "anomaly_overall": header.get("anomaly_overall", "N/A"),
    }


def build_ops_bootstrap() -> dict[str, Any]:
    manifest = _safe_read_json(DEFAULT_MANIFEST_JSON_PATH) or {}
    home_payload = _safe_read_json(DEFAULT_HOME_PAYLOAD_JSON_PATH) or {}
    sidebar = _safe_read_json(DEFAULT_SIDEBAR_JSON_PATH) or {}
    tabs = _safe_read_json(DEFAULT_TABS_JSON_PATH) or {}
    header = _safe_read_json(DEFAULT_HEADER_JSON_PATH) or {}

    status = _extract_status(home_payload, header)

    tabs_list = tabs.get("tabs") if isinstance(tabs.get("tabs"), list) else []
    sidebar_sections = sidebar.get("sections") if isinstance(sidebar.get("sections"), list) else []
    cards = home_payload.get("cards") if isinstance(home_payload.get("cards"), dict) else {}
    cards_list = cards.get("cards") if isinstance(cards.get("cards"), list) else []

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "header": header,
        "status": status,
        "sidebar": sidebar,
        "tabs": tabs,
        "home_payload": home_payload,
        "manifest": manifest,
        "summary": {
            "decision": status.get("decision", "N/A"),
            "badge_text": status.get("badge_text", "N/A"),
            "tabs_count": len(tabs_list),
            "sidebar_sections_count": len(sidebar_sections),
            "cards_count": len(cards_list),
        },
        "sources": {
            "manifest": {
                "path": str(DEFAULT_MANIFEST_JSON_PATH),
                "generated_at": _extract_generated_at(manifest),
                "exists": DEFAULT_MANIFEST_JSON_PATH.exists(),
            },
            "home_payload": {
                "path": str(DEFAULT_HOME_PAYLOAD_JSON_PATH),
                "generated_at": _extract_generated_at(home_payload),
                "exists": DEFAULT_HOME_PAYLOAD_JSON_PATH.exists(),
            },
            "sidebar": {
                "path": str(DEFAULT_SIDEBAR_JSON_PATH),
                "generated_at": _extract_generated_at(sidebar),
                "exists": DEFAULT_SIDEBAR_JSON_PATH.exists(),
            },
            "tabs": {
                "path": str(DEFAULT_TABS_JSON_PATH),
                "generated_at": _extract_generated_at(tabs),
                "exists": DEFAULT_TABS_JSON_PATH.exists(),
            },
            "header": {
                "path": str(DEFAULT_HEADER_JSON_PATH),
                "generated_at": _extract_generated_at(header),
                "exists": DEFAULT_HEADER_JSON_PATH.exists(),
            },
        },
    }