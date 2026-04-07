from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import BASE_DIR, DEFAULT_REPORT_DIR


DEFAULT_LOG_DIR = BASE_DIR / "data" / "logs"
DEFAULT_OPS_TIMELINE_JSON_PATH = DEFAULT_REPORT_DIR / "ops_timeline_latest.json"
DEFAULT_OPS_CYCLE_LOG_PATH = DEFAULT_LOG_DIR / "ops_cycle.log"
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


def _safe_read_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _parse_iso(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _from_timeline(limit: int) -> list[dict[str, Any]]:
    payload = _safe_read_json(DEFAULT_OPS_TIMELINE_JSON_PATH)
    rows = payload.get("events")
    if not isinstance(rows, list):
        return []

    items: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        timestamp = str(row.get("timestamp") or "").strip()
        title = str(row.get("title") or "").strip()
        status = str(row.get("status") or "UNKNOWN").strip() or "UNKNOWN"
        category = str(row.get("category") or "event").strip() or "event"
        if not timestamp or not title:
            continue
        items.append(
            {
                "timestamp": timestamp,
                "title": title,
                "status": status,
                "category": category,
            }
        )

    items = [item for item in items if _parse_iso(item.get("timestamp")) is not None]
    items.sort(key=lambda item: _parse_iso(item.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return items[: max(limit, 0)]


def _from_ops_cycle_log(limit: int) -> list[dict[str, Any]]:
    text = _safe_read_text(DEFAULT_OPS_CYCLE_LOG_PATH)
    if not text.strip():
        return []

    pattern = re.compile(
        r"\[(?P<index>\d+)\]\sstep:\s(?P<name>[^\n]+)\n"
        r"timestamp_start:\s(?P<start>[^\n]*)\n"
        r"timestamp_end:\s(?P<end>[^\n]*)\n"
        r"returncode:\s(?P<returncode>[^\n]*)\n"
        r"status:\s(?P<status>[^\n]*)\n"
        r"cmd:\s(?P<cmd>[^\n]*)",
        flags=re.MULTILINE,
    )

    rows: list[dict[str, Any]] = []
    for match in pattern.finditer(text):
        step_name = match.group("name").strip()
        end_timestamp = match.group("end").strip()
        status = match.group("status").strip() or "UNKNOWN"
        if not end_timestamp:
            continue
        rows.append(
            {
                "timestamp": end_timestamp,
                "title": step_name.replace("_", " ").title(),
                "status": status,
                "category": "ops_cycle_step",
            }
        )

    rows = [row for row in rows if _parse_iso(row.get("timestamp")) is not None]
    rows.sort(key=lambda row: _parse_iso(row.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return rows[: max(limit, 0)]


def build_ops_recent_events(limit: int = 5) -> dict[str, Any]:
    normalized_limit = min(max(int(limit), 0), 10)

    items = _from_timeline(normalized_limit)
    source_kind = "timeline"
    if not items:
        items = _from_ops_cycle_log(normalized_limit)
        source_kind = "ops_cycle_log"

    sources = {
        "timeline": {
            "path": _normalize_path(DEFAULT_OPS_TIMELINE_JSON_PATH),
            "exists": DEFAULT_OPS_TIMELINE_JSON_PATH.exists(),
        },
        "ops_cycle_log": {
            "path": _normalize_path(DEFAULT_OPS_CYCLE_LOG_PATH),
            "exists": DEFAULT_OPS_CYCLE_LOG_PATH.exists(),
        },
    }

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "items": items,
        "summary": {
            "item_count": len(items),
            "limit": normalized_limit,
            "source_kind": source_kind,
        },
        "status": {
            "ready": len(items) > 0,
            "fail_safe": True,
        },
        "sources": sources,
    }