from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import DEFAULT_REPORT_DIR


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_BOOTSTRAP_JSON_PATH = DEFAULT_REPORT_DIR / "ops_bootstrap_latest.json"
DEFAULT_HOME_PAYLOAD_JSON_PATH = DEFAULT_REPORT_DIR / "ops_home_payload_latest.json"
DEFAULT_CARDS_JSON_PATH = DEFAULT_REPORT_DIR / "ops_cards_latest.json"
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


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def _dummy_defaults() -> dict[str, Any]:
    return {
        "generated_at": _now_iso(),
        "mode": "preview",
        "schema_version": SCHEMA_VERSION,
        "header": {
            "generated_at": _now_iso(),
            "decision": "REVIEW",
            "badge_text": "REVIEW | Health B | WARNING",
            "health_score": 85,
            "health_grade": "B",
            "anomaly_overall": "WARNING",
            "last_updated": _now_iso(),
            "latest_archive_available": True,
        },
        "status": {
            "generated_at": _now_iso(),
            "decision": "REVIEW",
            "badge_text": "REVIEW | Health B | WARNING",
            "health_score": 85,
            "health_grade": "B",
            "anomaly_overall": "WARNING",
            "latest_daily_report": "data/reports/daily_report_preview.json",
            "latest_archive": "data/archives/ops_archive_preview.zip",
            "recommended_action": "プレビュー表示用ダミーデータです。実データ接続後に置き換えてください。",
            "recent_trend": {
                "release_decisions": ["review", "release", "review"],
                "health_scores": [85, 88, 82],
                "anomaly_overall": ["WARNING", "OK", "WARNING"],
            },
        },
        "cards": {
            "generated_at": _now_iso(),
            "cards": [
                {
                    "title": "Today's Decision",
                    "subtitle": "preview decision card",
                    "status": "REVIEW",
                    "path": "data/reports/ops_portal_latest.html",
                },
                {
                    "title": "Status Badge",
                    "subtitle": "REVIEW | Health B | WARNING",
                    "status": "REVIEW",
                    "path": "data/reports/status_badge_latest.json",
                },
                {
                    "title": "Latest Archive",
                    "subtitle": "preview archive artifact",
                    "status": "AVAILABLE",
                    "path": "data/archives/ops_archive_preview.zip",
                },
            ],
        },
        "navigation": {
            "sidebar": {
                "sections": [
                    {
                        "key": "today",
                        "title": "Today",
                        "default_open": True,
                        "items": [
                            {
                                "key": "ops_home",
                                "label": "Ops Home",
                                "path": "data/reports/ops_home_latest.html",
                                "icon": "home",
                            },
                            {
                                "key": "status_light",
                                "label": "Today's Decision (REVIEW)",
                                "path": "data/reports/ops_status_light_latest.json",
                                "icon": "pulse",
                            },
                        ],
                    }
                ]
            },
            "tabs": {
                "tabs": [
                    {
                        "key": "overview",
                        "title": "Overview",
                        "default": True,
                        "primary_path": "data/reports/ops_home_latest.html",
                        "related_paths": [
                            "data/reports/ops_status_light_latest.json",
                            "data/reports/ops_home_latest.html",
                        ],
                    }
                ]
            },
        },
        "sources": {
            "bootstrap": {
                "path": str(DEFAULT_BOOTSTRAP_JSON_PATH),
                "exists": DEFAULT_BOOTSTRAP_JSON_PATH.exists(),
            },
            "home_payload": {
                "path": str(DEFAULT_HOME_PAYLOAD_JSON_PATH),
                "exists": DEFAULT_HOME_PAYLOAD_JSON_PATH.exists(),
            },
            "cards": {
                "path": str(DEFAULT_CARDS_JSON_PATH),
                "exists": DEFAULT_CARDS_JSON_PATH.exists(),
            },
            "header": {
                "path": str(DEFAULT_HEADER_JSON_PATH),
                "exists": DEFAULT_HEADER_JSON_PATH.exists(),
            },
        },
    }


def merge_with_dummy_defaults(data: dict) -> dict:
    defaults = _dummy_defaults()

    def _merge(actual: Any, default: Any) -> Any:
        if isinstance(default, dict):
            actual_dict = actual if isinstance(actual, dict) else {}
            merged: dict[str, Any] = {}
            keys = set(default.keys()) | set(actual_dict.keys())
            for key in keys:
                merged[key] = _merge(actual_dict.get(key), default.get(key))
            return merged

        if isinstance(default, list):
            if isinstance(actual, list) and actual:
                return actual
            return deepcopy(default)

        if _is_missing(actual):
            return deepcopy(default)
        return actual

    return _merge(data, defaults)


def build_ops_preview_payload() -> dict[str, Any]:
    bootstrap = _safe_read_json(DEFAULT_BOOTSTRAP_JSON_PATH) or {}
    home_payload = _safe_read_json(DEFAULT_HOME_PAYLOAD_JSON_PATH) or {}
    cards_payload = _safe_read_json(DEFAULT_CARDS_JSON_PATH) or {}
    header_payload = _safe_read_json(DEFAULT_HEADER_JSON_PATH) or {}

    actual = {
        "generated_at": _now_iso(),
        "mode": "preview",
        "schema_version": SCHEMA_VERSION,
        "header": bootstrap.get("header") if isinstance(bootstrap.get("header"), dict) else header_payload,
        "status": bootstrap.get("status") if isinstance(bootstrap.get("status"), dict) else home_payload.get("status"),
        "cards": home_payload.get("cards") if isinstance(home_payload.get("cards"), dict) else cards_payload,
        "navigation": {
            "sidebar": bootstrap.get("sidebar") if isinstance(bootstrap.get("sidebar"), dict) else {},
            "tabs": bootstrap.get("tabs") if isinstance(bootstrap.get("tabs"), dict) else {},
        },
        "sources": {
            "bootstrap": {
                "path": str(DEFAULT_BOOTSTRAP_JSON_PATH),
                "exists": DEFAULT_BOOTSTRAP_JSON_PATH.exists(),
            },
            "home_payload": {
                "path": str(DEFAULT_HOME_PAYLOAD_JSON_PATH),
                "exists": DEFAULT_HOME_PAYLOAD_JSON_PATH.exists(),
            },
            "cards": {
                "path": str(DEFAULT_CARDS_JSON_PATH),
                "exists": DEFAULT_CARDS_JSON_PATH.exists(),
            },
            "header": {
                "path": str(DEFAULT_HEADER_JSON_PATH),
                "exists": DEFAULT_HEADER_JSON_PATH.exists(),
            },
        },
    }

    merged = merge_with_dummy_defaults(actual)
    merged["generated_at"] = _now_iso()
    merged["mode"] = "preview"
    merged["schema_version"] = SCHEMA_VERSION
    return merged