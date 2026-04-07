from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import BASE_DIR, DEFAULT_REPORT_DIR


DEFAULT_CONFIG_PATH = BASE_DIR / "config" / "ops_settings.json"
DEFAULT_ALERT_CENTER_PATH = DEFAULT_REPORT_DIR / "ops_alert_center_latest.json"
DEFAULT_RELEASE_READINESS_PATH = DEFAULT_REPORT_DIR / "release_readiness_latest.json"
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


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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


def build_ops_notification_settings() -> dict[str, Any]:
    settings = _safe_read_json(DEFAULT_CONFIG_PATH)
    alert_center = _safe_read_json(DEFAULT_ALERT_CENTER_PATH)
    release_readiness = _safe_read_json(DEFAULT_RELEASE_READINESS_PATH)

    anomaly = settings.get("anomaly") if isinstance(settings.get("anomaly"), dict) else {}

    notifications = {
        "notify_on_ok": bool(anomaly.get("notify_on_ok", False)),
        "notify_on_warning": bool(anomaly.get("notify_on_warning", True)),
        "notify_on_critical": bool(anomaly.get("notify_on_critical", True)),
    }

    thresholds = {
        "failed_count_warning": _to_int(anomaly.get("failed_count_warning"), 0),
        "failed_count_critical": _to_int(anomaly.get("failed_count_critical"), 0),
        "retry_queued_warning": _to_int(anomaly.get("retry_queued_warning"), 0),
        "retry_queued_critical": _to_int(anomaly.get("retry_queued_critical"), 0),
        "all_signal_zero_warning_days": _to_int(anomaly.get("all_signal_zero_warning_days"), 0),
        "smoke_failed_warning": _to_int(anomaly.get("smoke_failed_warning"), 0),
        "smoke_failed_critical": _to_int(anomaly.get("smoke_failed_critical"), 0),
    }

    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    channels = {
        "slack_configured": bool(slack_webhook_url),
        "slack_webhook_env": "SLACK_WEBHOOK_URL",
    }

    context = {
        "alert_center_overall": str(alert_center.get("overall") or "N/A"),
        "alert_count": _to_int((alert_center.get("summary") or {}).get("alert_count"), 0),
        "release_readiness_decision": str(release_readiness.get("decision") or "N/A"),
    }

    sources = {
        "ops_settings": _source_meta(DEFAULT_CONFIG_PATH, settings),
        "alert_center": _source_meta(DEFAULT_ALERT_CENTER_PATH, alert_center),
        "release_readiness": _source_meta(DEFAULT_RELEASE_READINESS_PATH, release_readiness),
    }
    missing_source_keys = [key for key, meta in sources.items() if not bool(meta.get("exists"))]
    partial = any(not bool(meta.get("loaded")) for meta in sources.values())

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "notifications": notifications,
        "thresholds": thresholds,
        "channels": channels,
        "context": context,
        "status": {
            "partial": partial,
            "ready": len(missing_source_keys) == 0,
            "missing_source_keys": missing_source_keys,
            "fail_safe": True,
        },
        "sources": sources,
    }