from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import DEFAULT_REPORT_DIR


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_HOME_PAYLOAD_JSON_PATH = DEFAULT_REPORT_DIR / "ops_home_payload_latest.json"
DEFAULT_CARDS_JSON_PATH = DEFAULT_REPORT_DIR / "ops_cards_latest.json"
DEFAULT_STATUS_LIGHT_JSON_PATH = DEFAULT_REPORT_DIR / "ops_status_light_latest.json"
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


def _normalize_path(value: Any) -> str:
    if value is None:
        return "N/A"

    text = str(value).strip()
    if not text:
        return "N/A"

    path_obj = Path(text)
    if path_obj.is_absolute():
        try:
            return str(path_obj.relative_to(BASE_DIR)).replace("\\", "/")
        except ValueError:
            return str(path_obj)

    return text.replace("\\", "/")


def _source_exists(path_value: str) -> bool:
    if path_value == "N/A":
        return False

    path_obj = Path(path_value)
    resolved = path_obj if path_obj.is_absolute() else BASE_DIR / path_value
    return resolved.exists()


def _widget(
    key: str,
    widget_type: str,
    title: str,
    source: str,
    order: int,
    source_selector: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "key": key,
        "widget_type": widget_type,
        "title": title,
        "source": source,
        "order": order,
        "source_exists": _source_exists(source),
    }
    if source_selector:
        payload["source_selector"] = source_selector
    return payload


def _card_widget_specs(cards_payload: dict[str, Any]) -> list[tuple[str, str, str, dict[str, Any] | None]]:
    cards = cards_payload.get("cards") if isinstance(cards_payload.get("cards"), list) else []
    by_title = {
        str(card.get("title") or "").strip(): card
        for card in cards
        if isinstance(card, dict)
    }

    desired = [
        ("decision_card", "decision_card", "Today's Decision"),
        ("status_badge_card", "status_badge_card", "Status Badge"),
        ("daily_dashboard_card", "dashboard_card", "Latest Daily Dashboard"),
        ("archive_card", "archive_card", "Latest Archive"),
        ("runbook_card", "runbook_card", "Runbook"),
    ]

    specs: list[tuple[str, str, str, dict[str, Any] | None]] = []
    for key, widget_type, title in desired:
        card = by_title.get(title)
        selector = {"match": {"title": title}}
        if isinstance(card, dict):
            selector["path"] = card.get("path")
        specs.append((key, widget_type, title, selector))

    return specs


def build_ops_widgets() -> dict[str, Any]:
    home_payload = _safe_read_json(DEFAULT_HOME_PAYLOAD_JSON_PATH) or {}
    cards = _safe_read_json(DEFAULT_CARDS_JSON_PATH) or {}
    status_light = _safe_read_json(DEFAULT_STATUS_LIGHT_JSON_PATH) or {}
    header = _safe_read_json(DEFAULT_HEADER_JSON_PATH) or {}

    home_source = _normalize_path(str(DEFAULT_HOME_PAYLOAD_JSON_PATH))
    cards_source = _normalize_path(str(DEFAULT_CARDS_JSON_PATH))
    status_source = _normalize_path(str(DEFAULT_STATUS_LIGHT_JSON_PATH))
    header_source = _normalize_path(str(DEFAULT_HEADER_JSON_PATH))

    widgets: list[dict[str, Any]] = [
        _widget(
            key="status_header",
            widget_type="header_status",
            title="System Status",
            source=header_source,
            order=1,
        ),
        _widget(
            key="status_summary",
            widget_type="status_summary",
            title="Operations Summary",
            source=status_source,
            order=2,
        ),
    ]

    next_order = 3
    for key, widget_type, title, selector in _card_widget_specs(cards):
        widgets.append(
            _widget(
                key=key,
                widget_type=widget_type,
                title=title,
                source=cards_source,
                order=next_order,
                source_selector=selector,
            )
        )
        next_order += 1

    widgets.append(
        _widget(
            key="home_cards_grid",
            widget_type="cards_grid",
            title="Top Cards",
            source=home_source,
            order=next_order,
            source_selector={"path": "cards.cards"},
        )
    )

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "widgets": widgets,
        "summary": {
            "widget_count": len(widgets),
            "header_exists": bool(header),
            "status_exists": bool(status_light),
            "cards_exists": bool(cards),
            "home_payload_exists": bool(home_payload),
        },
        "sources": {
            "header": {
                "path": header_source,
                "exists": DEFAULT_HEADER_JSON_PATH.exists(),
            },
            "status_light": {
                "path": status_source,
                "exists": DEFAULT_STATUS_LIGHT_JSON_PATH.exists(),
            },
            "cards": {
                "path": cards_source,
                "exists": DEFAULT_CARDS_JSON_PATH.exists(),
            },
            "home_payload": {
                "path": home_source,
                "exists": DEFAULT_HOME_PAYLOAD_JSON_PATH.exists(),
            },
        },
    }