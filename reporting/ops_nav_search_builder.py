from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import BASE_DIR, DEFAULT_REPORT_DIR


DEFAULT_SIDEBAR_PATH = DEFAULT_REPORT_DIR / "ops_sidebar_latest.json"
DEFAULT_TABS_PATH = DEFAULT_REPORT_DIR / "ops_tabs_latest.json"
DEFAULT_GUI_SCHEMA_PATH = DEFAULT_REPORT_DIR / "ops_gui_schema_latest.json"
DEFAULT_GUI_HANDOFF_PATH = DEFAULT_REPORT_DIR / "ops_gui_handoff_latest.json"
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


def _tokenize(*values: str) -> list[str]:
    text = " ".join(v for v in values if v).lower()
    text = text.replace("_", " ").replace("-", " ").replace("/", " ").replace(".", " ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    raw = re.split(r"\s+", text.strip()) if text.strip() else []
    tokens: list[str] = []
    seen: set[str] = set()
    stop = {
        "data",
        "reports",
        "docs",
        "latest",
        "json",
        "html",
        "md",
        "ops",
    }
    for token in raw:
        if not token or token in stop:
            continue
        if token not in seen:
            seen.add(token)
            tokens.append(token)
    return tokens


def _is_target_like(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    s = value.strip().lower()
    return s.startswith("data/") or s.startswith("docs/")


def _infer_category(target: str, hint: str) -> str:
    lower = target.lower()
    hint_lower = hint.lower()
    if lower.endswith(".html"):
        return "page"
    if lower.endswith(".md"):
        return "doc"
    if "schema" in hint_lower or "schema" in lower:
        return "schema"
    if "mock" in hint_lower or "api" in hint_lower:
        return "api"
    if "handoff" in hint_lower:
        return "handoff"
    return "report"


def _add_item(index: dict[str, dict[str, Any]], label: str, target: str, category: str, keywords: list[str]) -> None:
    target_norm = str(target or "").strip()
    label_norm = str(label or "").strip()
    if not target_norm or not label_norm:
        return

    entry = index.get(target_norm)
    if entry is None:
        index[target_norm] = {
            "label": label_norm,
            "keywords": _tokenize(label_norm, target_norm, *keywords),
            "target": target_norm,
            "category": category,
        }
        return

    merged = entry.get("keywords") if isinstance(entry.get("keywords"), list) else []
    merged.extend(_tokenize(label_norm, target_norm, *keywords))
    deduped: list[str] = []
    seen: set[str] = set()
    for keyword in merged:
        if keyword not in seen:
            seen.add(keyword)
            deduped.append(keyword)
    entry["keywords"] = deduped


def _collect_from_sidebar(index: dict[str, dict[str, Any]], payload: dict[str, Any]) -> None:
    sections = payload.get("sections") if isinstance(payload.get("sections"), list) else []
    for section in sections:
        if not isinstance(section, dict):
            continue
        section_key = str(section.get("key") or "")
        section_title = str(section.get("title") or "")
        items = section.get("items") if isinstance(section.get("items"), list) else []
        for item in items:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or item.get("key") or "")
            target = str(item.get("path") or "")
            if not _is_target_like(target):
                continue
            category = _infer_category(target, f"sidebar {section_key}")
            _add_item(
                index,
                label=label,
                target=target,
                category=category,
                keywords=[section_key, section_title, str(item.get("key") or ""), "sidebar", "navigation"],
            )


def _collect_from_tabs(index: dict[str, dict[str, Any]], payload: dict[str, Any]) -> None:
    tabs = payload.get("tabs") if isinstance(payload.get("tabs"), list) else []
    for tab in tabs:
        if not isinstance(tab, dict):
            continue
        key = str(tab.get("key") or "")
        title = str(tab.get("title") or key or "Tab")
        primary_path = str(tab.get("primary_path") or "")
        related = tab.get("related_paths") if isinstance(tab.get("related_paths"), list) else []

        if _is_target_like(primary_path):
            _add_item(
                index,
                label=title,
                target=primary_path,
                category=_infer_category(primary_path, f"tab {key}"),
                keywords=[key, "tab", "navigation", "primary"],
            )

        for rel in related:
            rel_path = str(rel or "")
            if not _is_target_like(rel_path):
                continue
            rel_name = Path(rel_path).name.replace("_latest", "")
            _add_item(
                index,
                label=f"{title}: {rel_name}",
                target=rel_path,
                category=_infer_category(rel_path, f"tab related {key}"),
                keywords=[key, title, "tab", "related"],
            )


def _collect_from_handoff(index: dict[str, dict[str, Any]], payload: dict[str, Any]) -> None:
    entrypoints = payload.get("entrypoints") if isinstance(payload.get("entrypoints"), dict) else {}
    for key, value in entrypoints.items():
        target = str(value or "")
        if not _is_target_like(target):
            continue
        label = key.replace("_", " ").title()
        _add_item(
            index,
            label=label,
            target=target,
            category=_infer_category(target, f"handoff entrypoint {key}"),
            keywords=["handoff", "entrypoint", key, "bootstrap", "preview", "mock api"],
        )

    preview = payload.get("preview") if isinstance(payload.get("preview"), dict) else {}
    for key, value in preview.items():
        target = str(value or "")
        if not _is_target_like(target):
            continue
        _add_item(
            index,
            label=key.replace("_", " ").title(),
            target=target,
            category=_infer_category(target, "handoff preview"),
            keywords=["handoff", "preview", key],
        )

    api_mock = payload.get("api_mock") if isinstance(payload.get("api_mock"), dict) else {}
    for key, value in api_mock.items():
        target = str(value or "")
        if not _is_target_like(target):
            continue
        _add_item(
            index,
            label=f"Mock API {key.title()}",
            target=target,
            category="api",
            keywords=["handoff", "mock", "api", key],
        )

    read_order = payload.get("read_order") if isinstance(payload.get("read_order"), list) else []
    for path in read_order:
        target = str(path or "")
        if not _is_target_like(target):
            continue
        _add_item(
            index,
            label=Path(target).name,
            target=target,
            category=_infer_category(target, "handoff read order"),
            keywords=["handoff", "read", "order", "archive"],
        )


def _collect_from_schema(index: dict[str, dict[str, Any]], payload: dict[str, Any]) -> None:
    top_level_keys = [
        "sidebar",
        "tabs",
        "widgets",
        "layout",
        "header",
        "home_payload",
        "bootstrap",
    ]

    for key in top_level_keys:
        obj = payload.get(key)
        if not isinstance(obj, dict):
            continue
        for field in ("path", "primary_path", "source"):
            target = str(obj.get(field) or "")
            if _is_target_like(target):
                _add_item(
                    index,
                    label=f"Schema {key.title()}",
                    target=target,
                    category=_infer_category(target, f"schema {key}"),
                    keywords=["schema", key, field],
                )
        for field in ("related_paths", "sources", "paths"):
            values = obj.get(field)
            if not isinstance(values, list):
                continue
            for val in values:
                target = str(val or "")
                if not _is_target_like(target):
                    continue
                _add_item(
                    index,
                    label=f"Schema {key.title()} {Path(target).name}",
                    target=target,
                    category=_infer_category(target, f"schema {key}"),
                    keywords=["schema", key, field],
                )

    _add_item(
        index,
        label="Archive",
        target="data/reports/artifact_index_latest.html",
        category="page",
        keywords=["archive", "artifacts", "history", "index"],
    )


def build_ops_nav_search() -> dict[str, Any]:
    sidebar = _safe_read_json(DEFAULT_SIDEBAR_PATH)
    tabs = _safe_read_json(DEFAULT_TABS_PATH)
    schema = _safe_read_json(DEFAULT_GUI_SCHEMA_PATH)
    handoff = _safe_read_json(DEFAULT_GUI_HANDOFF_PATH)

    item_index: dict[str, dict[str, Any]] = {}
    _collect_from_sidebar(item_index, sidebar)
    _collect_from_tabs(item_index, tabs)
    _collect_from_handoff(item_index, handoff)
    _collect_from_schema(item_index, schema)

    items = sorted(item_index.values(), key=lambda row: (str(row.get("category") or ""), str(row.get("label") or "")))

    sources = {
        "sidebar": _source_meta(DEFAULT_SIDEBAR_PATH, sidebar),
        "tabs": _source_meta(DEFAULT_TABS_PATH, tabs),
        "gui_schema": _source_meta(DEFAULT_GUI_SCHEMA_PATH, schema),
        "gui_handoff": _source_meta(DEFAULT_GUI_HANDOFF_PATH, handoff),
    }
    missing_source_keys = [key for key, meta in sources.items() if not bool(meta.get("exists"))]
    partial = any(not bool(meta.get("loaded")) for meta in sources.values())

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "items": items,
        "summary": {
            "item_count": len(items),
            "category_counts": {
                "page": sum(1 for item in items if item.get("category") == "page"),
                "report": sum(1 for item in items if item.get("category") == "report"),
                "schema": sum(1 for item in items if item.get("category") == "schema"),
                "api": sum(1 for item in items if item.get("category") == "api"),
                "doc": sum(1 for item in items if item.get("category") == "doc"),
                "handoff": sum(1 for item in items if item.get("category") == "handoff"),
            },
        },
        "status": {
            "partial": partial,
            "ready": len(missing_source_keys) == 0,
            "missing_source_keys": missing_source_keys,
            "fail_safe": True,
        },
        "sources": sources,
    }
