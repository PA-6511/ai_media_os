from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import BASE_DIR, DEFAULT_REPORT_DIR


DEFAULT_DOCS_DIR = BASE_DIR / "docs"
DEFAULT_HANDOFF_PATH = DEFAULT_REPORT_DIR / "ops_gui_handoff_latest.json"
DEFAULT_BUNDLE_PATH = DEFAULT_REPORT_DIR / "ops_gui_bundle_manifest_latest.json"
DEFAULT_BOOTSTRAP_PATH = DEFAULT_REPORT_DIR / "ops_bootstrap_latest.json"
DEFAULT_GUI_SCHEMA_PATH = DEFAULT_REPORT_DIR / "ops_gui_schema_latest.json"
DEFAULT_MOCK_API_PATH = DEFAULT_REPORT_DIR / "mock_api_home_latest.json"
DEFAULT_PREVIEW_PATH = DEFAULT_REPORT_DIR / "ops_gui_preview_latest.html"
DEFAULT_RUNBOOK_PATH = DEFAULT_DOCS_DIR / "runbook_latest.md"
DEFAULT_DAILY_CHECKLIST_PATH = DEFAULT_DOCS_DIR / "daily_checklist_latest.md"
DEFAULT_GO_LIVE_CHECKLIST_PATH = DEFAULT_DOCS_DIR / "gui_go_live_checklist_latest.md"
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


def _path_or_na(path: Path) -> str:
    return _normalize_path(path) if path.exists() and path.is_file() else "N/A"


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def build_ops_gui_starter_pack() -> dict[str, Any]:
    handoff = _safe_read_json(DEFAULT_HANDOFF_PATH)
    bundle = _safe_read_json(DEFAULT_BUNDLE_PATH)

    handoff_read_order = handoff.get("read_order") if isinstance(handoff.get("read_order"), list) else []
    first_read_defaults = [
        _normalize_path(DEFAULT_BOOTSTRAP_PATH),
        _normalize_path(DEFAULT_GUI_SCHEMA_PATH),
        _normalize_path(DEFAULT_MOCK_API_PATH),
        _normalize_path(DEFAULT_PREVIEW_PATH),
    ]
    first_read = _dedupe_keep_order([*(str(x) for x in handoff_read_order), *first_read_defaults])[:8]

    bundle_entry = bundle.get("entrypoints") if isinstance(bundle.get("entrypoints"), dict) else {}
    handoff_entry = handoff.get("entrypoints") if isinstance(handoff.get("entrypoints"), dict) else {}
    handoff_preview = handoff.get("preview") if isinstance(handoff.get("preview"), dict) else {}
    handoff_api = handoff.get("api_mock") if isinstance(handoff.get("api_mock"), dict) else {}

    entrypoints = {
        "bootstrap": str(handoff_entry.get("bootstrap") or bundle_entry.get("bootstrap") or _path_or_na(DEFAULT_BOOTSTRAP_PATH)),
        "gui_schema": str(handoff_entry.get("gui_schema") or _path_or_na(DEFAULT_GUI_SCHEMA_PATH)),
        "home_payload": str(handoff_entry.get("home_payload") or bundle_entry.get("home_payload") or "N/A"),
        "mock_api": str(handoff_api.get("home") or bundle_entry.get("mock_api") or _path_or_na(DEFAULT_MOCK_API_PATH)),
        "preview_html": str(handoff_preview.get("gui_preview_html") or bundle_entry.get("preview_html") or _path_or_na(DEFAULT_PREVIEW_PATH)),
    }

    preview_files = _dedupe_keep_order(
        [
            entrypoints["preview_html"],
            _normalize_path(DEFAULT_REPORT_DIR / "ops_home_latest.html"),
            _normalize_path(DEFAULT_REPORT_DIR / "ops_portal_latest.html"),
        ]
    )

    docs = {
        "runbook": _path_or_na(DEFAULT_RUNBOOK_PATH),
        "daily_checklist": _path_or_na(DEFAULT_DAILY_CHECKLIST_PATH),
        "gui_go_live_checklist": _path_or_na(DEFAULT_GO_LIVE_CHECKLIST_PATH),
    }

    next_steps = [
        "python3 -m gui.run_mock_server を実行して mock API を起動する",
        "ops_gui_preview_latest.html を開いて UI 全体構成を確認する",
        "bootstrap -> gui_schema -> mock_api の順でデータ読み込みを実装する",
        "sidebar/tabs/widgets/layout を使って初期画面を組み立てる",
        "gui_go_live_checklist_latest.md で go-live 判定項目を確認する",
    ]

    sources = {
        "handoff": _source_meta(DEFAULT_HANDOFF_PATH, handoff),
        "bundle_manifest": _source_meta(DEFAULT_BUNDLE_PATH, bundle),
    }
    missing_source_keys = [key for key, meta in sources.items() if not bool(meta.get("exists"))]
    partial = any(not bool(meta.get("loaded")) for meta in sources.values())

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "first_read": first_read,
        "entrypoints": entrypoints,
        "preview_files": preview_files,
        "api_mock": {
            "home": entrypoints["mock_api"],
            "health_endpoint": "http://127.0.0.1:8765/health",
        },
        "docs": docs,
        "next_steps": next_steps,
        "summary": {
            "first_read_count": len(first_read),
            "preview_file_count": len(preview_files),
            "doc_count": len([v for v in docs.values() if v != "N/A"]),
        },
        "status": {
            "partial": partial,
            "ready": len(missing_source_keys) == 0,
            "missing_source_keys": missing_source_keys,
            "fail_safe": True,
        },
        "sources": sources,
    }