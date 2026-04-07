from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ops.release_readiness_writer import DEFAULT_HISTORY_PATH


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_iso_datetime(value: Any) -> datetime | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    # Python fromisoformat does not accept trailing Z on older runtimes.
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _load_history_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        return []

    try:
        raw_lines = [
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except OSError:
        return []

    rows: list[dict[str, Any]] = []
    for line in raw_lines:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _normalize_daily_latest(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest_by_date: dict[str, dict[str, Any]] = {}

    for row in rows:
        dt = _parse_iso_datetime(row.get("generated_at"))
        if dt is None:
            continue

        date_key = dt.date().isoformat()
        current = latest_by_date.get(date_key)
        if current is None or dt > current["_dt"]:
            latest_by_date[date_key] = {
                "_dt": dt,
                "date": date_key,
                "generated_at": row.get("generated_at"),
                "decision": str(row.get("decision", "N/A")),
                "health_score": row.get("health_score", "N/A"),
                "anomaly_overall": row.get("anomaly_overall", "N/A"),
            }

    normalized = list(latest_by_date.values())
    normalized.sort(key=lambda item: item["_dt"], reverse=True)
    return normalized


def _count_decisions(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"release": 0, "review": 0, "hold": 0}
    for row in rows:
        decision = str(row.get("decision", "")).strip().lower()
        if decision in counts:
            counts[decision] += 1
    return counts


def build_release_readiness_trend(limit_days: int = 7) -> dict:
    """release readiness 履歴から日次トレンドサマリーを構築する。"""
    rows = _load_history_rows(DEFAULT_HISTORY_PATH)
    daily_latest = _normalize_daily_latest(rows)

    if limit_days > 0:
        daily_latest = daily_latest[:limit_days]

    counts = _count_decisions(daily_latest)
    latest_decision = daily_latest[0]["decision"] if daily_latest else "N/A"

    recent_days = [
        {
            "date": row.get("date"),
            "decision": row.get("decision", "N/A"),
            "health_score": row.get("health_score", "N/A"),
            "anomaly_overall": row.get("anomaly_overall", "N/A"),
        }
        for row in daily_latest
    ]

    return {
        "generated_at": _now_iso(),
        "total_days": len(daily_latest),
        "release_count": counts["release"],
        "review_count": counts["review"],
        "hold_count": counts["hold"],
        "latest_decision": latest_decision,
        "recent_days": recent_days,
        "source": {
            "history_path": str(DEFAULT_HISTORY_PATH),
            "history_records": len(rows),
            "limit_days": limit_days,
        },
    }
