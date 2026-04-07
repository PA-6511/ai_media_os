from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = BASE_DIR / "data" / "reports"
DEFAULT_STATUS_LIGHT_PATH = DEFAULT_REPORT_DIR / "ops_status_light_latest.json"
DEFAULT_NAVIGATION_PATH = DEFAULT_REPORT_DIR / "ops_navigation_latest.json"
DEFAULT_CARDS_PATH = DEFAULT_REPORT_DIR / "ops_cards_latest.json"
DEFAULT_TIMESTAMPS_PATH = DEFAULT_REPORT_DIR / "ops_timestamps_latest.json"
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


def build_ops_home_payload() -> dict[str, Any]:
    status = _safe_read_json(DEFAULT_STATUS_LIGHT_PATH) or {}
    navigation = _safe_read_json(DEFAULT_NAVIGATION_PATH) or {}
    cards = _safe_read_json(DEFAULT_CARDS_PATH) or {}
    timestamps = _safe_read_json(DEFAULT_TIMESTAMPS_PATH) or {}

    cards_count = 0
    cards_list = cards.get("cards")
    if isinstance(cards_list, list):
        cards_count = len(cards_list)

    timestamps_count = 0
    timestamps_list = timestamps.get("timestamps")
    if isinstance(timestamps_list, list):
        timestamps_count = len(timestamps_list)

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "navigation": navigation,
        "cards": cards,
        "timestamps": timestamps,
        "summary": {
            "decision": status.get("decision", "N/A"),
            "badge_text": status.get("badge_text", "N/A"),
            "cards_count": cards_count,
            "timestamps_count": timestamps_count,
        },
        "sources": {
            "status": {
                "path": str(DEFAULT_STATUS_LIGHT_PATH),
                "generated_at": _extract_generated_at(status),
                "exists": DEFAULT_STATUS_LIGHT_PATH.exists(),
            },
            "navigation": {
                "path": str(DEFAULT_NAVIGATION_PATH),
                "generated_at": _extract_generated_at(navigation),
                "exists": DEFAULT_NAVIGATION_PATH.exists(),
            },
            "cards": {
                "path": str(DEFAULT_CARDS_PATH),
                "generated_at": _extract_generated_at(cards),
                "exists": DEFAULT_CARDS_PATH.exists(),
            },
            "timestamps": {
                "path": str(DEFAULT_TIMESTAMPS_PATH),
                "generated_at": _extract_generated_at(timestamps),
                "exists": DEFAULT_TIMESTAMPS_PATH.exists(),
            },
        },
    }
