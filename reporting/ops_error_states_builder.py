from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import BASE_DIR, DEFAULT_REPORT_DIR


DEFAULT_BOOTSTRAP_PATH = DEFAULT_REPORT_DIR / "ops_bootstrap_latest.json"
DEFAULT_MOCK_API_PATH = DEFAULT_REPORT_DIR / "mock_api_home_latest.json"
DEFAULT_INTEGRITY_PATH = DEFAULT_REPORT_DIR / "ops_gui_integrity_latest.json"
DEFAULT_HEALTH_PATH = DEFAULT_REPORT_DIR / "ops_gui_health_latest.json"
DEFAULT_ALERT_CENTER_PATH = DEFAULT_REPORT_DIR / "ops_alert_center_latest.json"
DEFAULT_READINESS_PATH = DEFAULT_REPORT_DIR / "release_readiness_latest.json"
DEFAULT_CONFIG_SUMMARY_PATH = DEFAULT_REPORT_DIR / "ops_config_summary_latest.json"
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


def _lower(value: Any) -> str:
    return str(value or "").strip().lower()


def _upper(value: Any) -> str:
    return str(value or "").strip().upper()


def build_ops_error_states() -> dict[str, Any]:
    bootstrap = _safe_read_json(DEFAULT_BOOTSTRAP_PATH)
    mock_api = _safe_read_json(DEFAULT_MOCK_API_PATH)
    integrity = _safe_read_json(DEFAULT_INTEGRITY_PATH)
    health = _safe_read_json(DEFAULT_HEALTH_PATH)
    alert_center = _safe_read_json(DEFAULT_ALERT_CENTER_PATH)
    readiness = _safe_read_json(DEFAULT_READINESS_PATH)
    config_summary = _safe_read_json(DEFAULT_CONFIG_SUMMARY_PATH)

    anomaly_cfg = config_summary.get("anomaly") if isinstance(config_summary.get("anomaly"), dict) else {}
    retry_warn_threshold = _safe_int(anomaly_cfg.get("retry_queued_warning"), 5)
    retry_critical_threshold = _safe_int(anomaly_cfg.get("retry_queued_critical"), 10)

    anomaly_overall = _upper(
        health.get("anomaly_overall")
        or (alert_center.get("signals") if isinstance(alert_center.get("signals"), dict) else {}).get("status_light", {}).get("anomaly_overall")
    )
    integrity_overall = _upper(integrity.get("overall"))
    retry_queued = _safe_int(
        readiness.get("retry_queued")
        or (alert_center.get("signals") if isinstance(alert_center.get("signals"), dict) else {}).get("retry_queue", {}).get("queued")
    )

    states: list[dict[str, Any]] = [
        {
            "code": "bootstrap_missing",
            "title": "Bootstrap Missing",
            "message": "GUI起動用データが見つかりません。",
            "recommended_action": "python3 -m reporting.run_ops_bootstrap_build を実行してください。",
            "severity": "warning",
            "active": not DEFAULT_BOOTSTRAP_PATH.exists() or not bool(bootstrap),
            "context": {
                "path": _normalize_path(DEFAULT_BOOTSTRAP_PATH),
                "exists": DEFAULT_BOOTSTRAP_PATH.exists(),
            },
        },
        {
            "code": "mock_api_unavailable",
            "title": "Mock API Unavailable",
            "message": "mock API 用データが取得できません。",
            "recommended_action": "python3 -m reporting.run_mock_api_build と python3 -m gui.run_mock_server を確認してください。",
            "severity": "warning",
            "active": not DEFAULT_MOCK_API_PATH.exists() or not bool(mock_api),
            "context": {
                "path": _normalize_path(DEFAULT_MOCK_API_PATH),
                "exists": DEFAULT_MOCK_API_PATH.exists(),
                "health_endpoint": "http://127.0.0.1:8765/health",
            },
        },
        {
            "code": "anomaly_warning",
            "title": "Anomaly Warning",
            "message": "anomaly が WARNING のため監視強化が必要です。",
            "recommended_action": "ops_alert_center_latest.json と daily report を確認して要因を切り分けてください。",
            "severity": "warning",
            "active": anomaly_overall == "WARNING",
            "context": {
                "anomaly_overall": anomaly_overall or "UNKNOWN",
            },
        },
        {
            "code": "anomaly_critical",
            "title": "Anomaly Critical",
            "message": "anomaly が CRITICAL のため通常運用継続は推奨されません。",
            "recommended_action": "復旧完了までリリース判断を hold にし、ops cycle を再実行してください。",
            "severity": "critical",
            "active": anomaly_overall == "CRITICAL",
            "context": {
                "anomaly_overall": anomaly_overall or "UNKNOWN",
            },
        },
        {
            "code": "retry_queue_pending",
            "title": "Retry Queue Pending",
            "message": "retry queue に未解決ジョブがあります。",
            "recommended_action": "失敗ジョブのログを確認し、次回サイクルで再試行または手動復旧を実施してください。",
            "severity": "warning",
            "active": retry_queued >= max(1, retry_warn_threshold),
            "context": {
                "retry_queued": retry_queued,
                "warning_threshold": retry_warn_threshold,
            },
        },
        {
            "code": "retry_queue_critical",
            "title": "Retry Queue Critical",
            "message": "retry queue が臨界値を超えています。",
            "recommended_action": "障害原因を優先調査し、未解決キューを解消するまで GUI 表示を制限してください。",
            "severity": "critical",
            "active": retry_queued >= max(retry_warn_threshold + 1, retry_critical_threshold),
            "context": {
                "retry_queued": retry_queued,
                "critical_threshold": retry_critical_threshold,
            },
        },
        {
            "code": "integrity_warning",
            "title": "Integrity Warning",
            "message": "GUI成果物の整合性チェックで WARNING が検出されました。",
            "recommended_action": "python3 -m reporting.run_ops_gui_integrity_build を実行し、missing_refs を修正してください。",
            "severity": "warning",
            "active": integrity_overall == "WARNING",
            "context": {
                "integrity_overall": integrity_overall or "UNKNOWN",
                "warning_count": _safe_int((integrity.get("summary") if isinstance(integrity.get("summary"), dict) else {}).get("warning_count")),
            },
        },
        {
            "code": "integrity_fail",
            "title": "Integrity Failed",
            "message": "GUI成果物の整合性チェックが FAIL です。",
            "recommended_action": "不足ファイルを再生成し、FAIL が 0 になるまでリリース導線を停止してください。",
            "severity": "critical",
            "active": integrity_overall == "FAIL",
            "context": {
                "integrity_overall": integrity_overall or "UNKNOWN",
                "fail_count": _safe_int((integrity.get("summary") if isinstance(integrity.get("summary"), dict) else {}).get("fail_count")),
            },
        },
    ]

    states.sort(key=lambda row: (_lower(row.get("severity")), _lower(row.get("code"))))

    sources = {
        "bootstrap": _source_meta(DEFAULT_BOOTSTRAP_PATH, bootstrap),
        "mock_api": _source_meta(DEFAULT_MOCK_API_PATH, mock_api),
        "gui_integrity": _source_meta(DEFAULT_INTEGRITY_PATH, integrity),
        "gui_health": _source_meta(DEFAULT_HEALTH_PATH, health),
        "alert_center": _source_meta(DEFAULT_ALERT_CENTER_PATH, alert_center),
        "release_readiness": _source_meta(DEFAULT_READINESS_PATH, readiness),
        "config_summary": _source_meta(DEFAULT_CONFIG_SUMMARY_PATH, config_summary),
    }
    missing_source_keys = [key for key, meta in sources.items() if not bool(meta.get("exists"))]
    partial = any(not bool(meta.get("loaded")) for meta in sources.values())

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "states": states,
        "summary": {
            "state_count": len(states),
            "active_count": sum(1 for row in states if bool(row.get("active"))),
            "warning_count": sum(1 for row in states if _lower(row.get("severity")) == "warning"),
            "critical_count": sum(1 for row in states if _lower(row.get("severity")) == "critical"),
        },
        "status": {
            "partial": partial,
            "ready": len(missing_source_keys) == 0,
            "missing_source_keys": missing_source_keys,
            "fail_safe": True,
        },
        "sources": sources,
    }
