from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_KPI_DIR = BASE_DIR / "data" / "kpi"
DEFAULT_KPI_SNAPSHOTS_PATH = DEFAULT_KPI_DIR / "kpi_snapshots.jsonl"
DEFAULT_LATEST_KPI_PATH = DEFAULT_KPI_DIR / "kpi_snapshot_latest.json"


def _snapshot_signature(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "latest_daily_report": snapshot.get("latest_daily_report"),
        "latest_weekly_report": snapshot.get("latest_weekly_report"),
        "latest_monthly_report": snapshot.get("latest_monthly_report"),
        "latest_archive": snapshot.get("latest_archive"),
        "archive_count": snapshot.get("archive_count"),
        "anomaly_overall": snapshot.get("anomaly_overall"),
        "alert_total": snapshot.get("alert_total"),
        "health_score": snapshot.get("health_score"),
        "health_grade": snapshot.get("health_grade"),
        "success_count": snapshot.get("success_count"),
        "skipped_count": snapshot.get("skipped_count"),
        "failed_count": snapshot.get("failed_count"),
        "draft_count": snapshot.get("draft_count"),
        "retry_queued_count": snapshot.get("retry_queued_count"),
        "combined_count": snapshot.get("combined_count"),
        "price_only_count": snapshot.get("price_only_count"),
        "release_only_count": snapshot.get("release_only_count"),
    }


def _load_last_snapshot(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None

    try:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            return None
        payload = json.loads(lines[-1])
    except Exception:
        return None

    return payload if isinstance(payload, dict) else None


def append_kpi_snapshot(snapshot: dict) -> str:
    """KPI snapshot を JSONL に追記保存する。重複時は追記しない。"""
    DEFAULT_KPI_DIR.mkdir(parents=True, exist_ok=True)
    path = DEFAULT_KPI_SNAPSHOTS_PATH

    last_snapshot = _load_last_snapshot(path)
    if last_snapshot is not None and _snapshot_signature(last_snapshot) == _snapshot_signature(snapshot):
        return str(path)

    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(snapshot, ensure_ascii=False) + "\n")
    return str(path)


def write_latest_kpi_snapshot(snapshot: dict) -> str:
    """最新 KPI snapshot を JSON で上書き保存する。"""
    DEFAULT_KPI_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_LATEST_KPI_PATH.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(DEFAULT_LATEST_KPI_PATH)
