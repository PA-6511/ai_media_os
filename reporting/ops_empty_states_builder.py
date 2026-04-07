from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import BASE_DIR, DEFAULT_REPORT_DIR


DEFAULT_RECENT_EVENTS_PATH = DEFAULT_REPORT_DIR / "ops_recent_events_latest.json"
DEFAULT_ALERT_CENTER_PATH = DEFAULT_REPORT_DIR / "ops_alert_center_latest.json"
DEFAULT_TIMELINE_PATH = DEFAULT_REPORT_DIR / "ops_timeline_latest.json"
DEFAULT_NAV_SEARCH_PATH = DEFAULT_REPORT_DIR / "ops_nav_search_latest.json"
DEFAULT_READINESS_PATH = DEFAULT_REPORT_DIR / "release_readiness_latest.json"
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


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def build_ops_empty_states() -> dict[str, Any]:
    recent_events = _safe_read_json(DEFAULT_RECENT_EVENTS_PATH)
    alert_center = _safe_read_json(DEFAULT_ALERT_CENTER_PATH)
    timeline = _safe_read_json(DEFAULT_TIMELINE_PATH)
    nav_search = _safe_read_json(DEFAULT_NAV_SEARCH_PATH)
    readiness = _safe_read_json(DEFAULT_READINESS_PATH)

    recent_count = _safe_int((recent_events.get("summary") if isinstance(recent_events.get("summary"), dict) else {}).get("item_count"))
    alerts_count = _safe_int((alert_center.get("summary") if isinstance(alert_center.get("summary"), dict) else {}).get("alert_count"))
    timeline_count = _safe_int((timeline.get("summary") if isinstance(timeline.get("summary"), dict) else {}).get("event_count"))
    nav_count = len(nav_search.get("items")) if isinstance(nav_search.get("items"), list) else 0
    retry_queued = _safe_int(
        readiness.get("retry_queued")
        or (alert_center.get("signals") if isinstance(alert_center.get("signals"), dict) else {}).get("retry_queue", {}).get("queued")
    )

    states: list[dict[str, Any]] = [
        {
            "key": "no_recent_events",
            "title": "最近のイベントはありません",
            "message": "直近の運用イベントはまだ記録されていません。",
            "action_label": "Ops Cycle を実行",
            "action_target": "python3 -m ops.run_ops_cycle",
            "active": recent_count == 0,
            "context": {
                "item_count": recent_count,
                "source": _normalize_path(DEFAULT_RECENT_EVENTS_PATH),
            },
        },
        {
            "key": "retry_queue_empty",
            "title": "再試行キューは空です",
            "message": "現在、再試行待ちのジョブはありません。",
            "action_label": "運用ログを見る",
            "action_target": "data/logs/ops_cycle.log",
            "active": retry_queued == 0,
            "context": {
                "retry_queued": retry_queued,
                "source": _normalize_path(DEFAULT_READINESS_PATH),
            },
        },
        {
            "key": "no_alerts",
            "title": "アラートはありません",
            "message": "現在表示対象のアラートは 0 件です。",
            "action_label": "Alert Center を更新",
            "action_target": "python3 -m reporting.run_ops_alert_center_build",
            "active": alerts_count == 0,
            "context": {
                "alert_count": alerts_count,
                "source": _normalize_path(DEFAULT_ALERT_CENTER_PATH),
            },
        },
        {
            "key": "timeline_empty",
            "title": "タイムライン項目がありません",
            "message": "表示できる運用履歴がまだありません。",
            "action_label": "Timeline を再生成",
            "action_target": "python3 -m reporting.run_ops_timeline_build",
            "active": timeline_count == 0,
            "context": {
                "event_count": timeline_count,
                "source": _normalize_path(DEFAULT_TIMELINE_PATH),
            },
        },
        {
            "key": "nav_search_no_match",
            "title": "一致するナビゲーションがありません",
            "message": "検索条件に一致する画面や成果物が見つかりませんでした。",
            "action_label": "検索インデックスを更新",
            "action_target": "python3 -m reporting.run_ops_nav_search_build",
            "active": nav_count == 0,
            "context": {
                "item_count": nav_count,
                "source": _normalize_path(DEFAULT_NAV_SEARCH_PATH),
            },
        },
    ]

    sources = {
        "recent_events": _source_meta(DEFAULT_RECENT_EVENTS_PATH, recent_events),
        "alert_center": _source_meta(DEFAULT_ALERT_CENTER_PATH, alert_center),
        "timeline": _source_meta(DEFAULT_TIMELINE_PATH, timeline),
        "nav_search": _source_meta(DEFAULT_NAV_SEARCH_PATH, nav_search),
        "release_readiness": _source_meta(DEFAULT_READINESS_PATH, readiness),
    }
    missing_source_keys = [key for key, meta in sources.items() if not bool(meta.get("exists"))]
    partial = any(not bool(meta.get("loaded")) for meta in sources.values())

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "states": states,
        "summary": {
            "state_count": len(states),
            "active_count": sum(1 for state in states if bool(state.get("active"))),
            "recent_events_count": recent_count,
            "alerts_count": alerts_count,
            "timeline_count": timeline_count,
            "nav_search_count": nav_count,
            "retry_queued": retry_queued,
        },
        "status": {
            "partial": partial,
            "ready": len(missing_source_keys) == 0,
            "missing_source_keys": missing_source_keys,
            "fail_safe": True,
        },
        "sources": sources,
    }
