from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = BASE_DIR / "data" / "reports"
DEFAULT_MANIFEST_PATH = DEFAULT_REPORT_DIR / "ops_manifest_latest.json"
DEFAULT_NAVIGATION_PATH = DEFAULT_REPORT_DIR / "ops_navigation_latest.json"
DEFAULT_CARDS_PATH = DEFAULT_REPORT_DIR / "ops_cards_latest.json"
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


def _to_rel_path(value: Any) -> str | None:
    if not value:
        return None

    text = str(value).strip()
    if not text:
        return None

    p = Path(text)
    if p.is_absolute():
        try:
            return str(p.relative_to(BASE_DIR)).replace("\\", "/")
        except ValueError:
            return str(p)

    return text.replace("\\", "/")


def _find_card_path(cards: list[dict[str, Any]], title: str) -> str | None:
    target = title.lower()
    for card in cards:
        ctitle = str(card.get("title") or "").strip().lower()
        if ctitle == target:
            return _to_rel_path(card.get("path"))
    return None


def _tab(
    key: str,
    title: str,
    default: bool,
    primary_path: Any,
    related_paths: list[Any] | None = None,
) -> dict[str, Any]:
    related = [_to_rel_path(v) for v in (related_paths or [])]
    related = [v for v in related if v]

    return {
        "key": key,
        "title": title,
        "default": default,
        "primary_path": _to_rel_path(primary_path),
        "related_paths": related,
    }


def _build_tabs_from_navigation(nav: dict[str, Any], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    tabs_src = nav.get("tabs") if isinstance(nav.get("tabs"), list) else []
    tabs: list[dict[str, Any]] = []

    for idx, tab in enumerate(tabs_src):
        if not isinstance(tab, dict):
            continue

        key = str(tab.get("key") or tab.get("id") or f"tab_{idx}").strip().lower().replace(" ", "_")
        title = str(tab.get("title") or tab.get("label") or key).strip()
        default = bool(tab.get("default", idx == 0))
        primary_path = tab.get("primary_path") or tab.get("path") or tab.get("href")
        related_paths = tab.get("related_paths") if isinstance(tab.get("related_paths"), list) else []

        tabs.append(_tab(key, title, default, primary_path, related_paths))

    # navigation 側に tabs があっても primary_path が空なら manifest で補完する。
    for tab in tabs:
        if tab.get("primary_path"):
            continue
        if tab["key"] == "overview":
            tab["primary_path"] = _to_rel_path(manifest.get("ops_home_html"))
        elif tab["key"] == "dashboards":
            tab["primary_path"] = _to_rel_path(manifest.get("daily_dashboard_html"))
        elif tab["key"] == "reports":
            tab["primary_path"] = _to_rel_path(manifest.get("ops_summary"))
        elif tab["key"] == "operations":
            tab["primary_path"] = _to_rel_path(manifest.get("ops_portal_html"))
        elif tab["key"] == "docs":
            tab["primary_path"] = _to_rel_path(manifest.get("daily_checklist_md"))

    return tabs


def _build_fallback_tabs(manifest: dict[str, Any], cards: dict[str, Any]) -> list[dict[str, Any]]:
    cards_list = cards.get("cards") if isinstance(cards.get("cards"), list) else []

    overview_path = _to_rel_path(manifest.get("ops_home_html")) or _find_card_path(cards_list, "Ops Home")
    dashboards_path = _to_rel_path(manifest.get("daily_dashboard_html")) or _find_card_path(cards_list, "Latest Daily Dashboard")
    reports_path = _to_rel_path(manifest.get("ops_summary")) or _find_card_path(cards_list, "Latest Summary JSON")
    operations_path = _to_rel_path(manifest.get("ops_portal_html")) or _find_card_path(cards_list, "Ops Portal")
    docs_path = _to_rel_path(manifest.get("daily_checklist_md")) or _find_card_path(cards_list, "Daily Checklist")

    return [
        _tab(
            "overview",
            "Overview",
            True,
            overview_path,
            [manifest.get("status_light"), manifest.get("ops_home_html")],
        ),
        _tab(
            "dashboards",
            "Dashboards",
            False,
            dashboards_path,
            [
                manifest.get("daily_dashboard_html"),
                manifest.get("weekly_dashboard_html"),
                manifest.get("monthly_dashboard_html"),
            ],
        ),
        _tab(
            "reports",
            "Reports",
            False,
            reports_path,
            [
                manifest.get("ops_summary"),
                manifest.get("ops_api_payload"),
                manifest.get("release_readiness_json"),
            ],
        ),
        _tab(
            "operations",
            "Operations",
            False,
            operations_path,
            [manifest.get("ops_portal_html"), manifest.get("artifact_index_html")],
        ),
        _tab(
            "docs",
            "Docs",
            False,
            docs_path,
            [manifest.get("daily_checklist_md"), manifest.get("runbook_md")],
        ),
    ]


def build_ops_tabs() -> dict[str, Any]:
    manifest = _safe_read_json(DEFAULT_MANIFEST_PATH) or {}
    navigation = _safe_read_json(DEFAULT_NAVIGATION_PATH) or {}
    cards = _safe_read_json(DEFAULT_CARDS_PATH) or {}

    tabs = _build_tabs_from_navigation(navigation, manifest)
    if not tabs:
        tabs = _build_fallback_tabs(manifest, cards)

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "tabs": tabs,
        "meta": {
            "source_manifest_exists": DEFAULT_MANIFEST_PATH.exists(),
            "source_navigation_exists": DEFAULT_NAVIGATION_PATH.exists(),
            "source_cards_exists": DEFAULT_CARDS_PATH.exists(),
        },
    }
