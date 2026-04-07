from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipelines.retry_queue_store import list_queue_items
from reporting.artifact_index_builder import BASE_DIR, DEFAULT_REPORT_DIR


DEFAULT_STATUS_LIGHT_JSON_PATH = DEFAULT_REPORT_DIR / "ops_status_light_latest.json"
DEFAULT_RELEASE_READINESS_JSON_PATH = DEFAULT_REPORT_DIR / "release_readiness_latest.json"
DEFAULT_ANOMALY_LOG_PATH = BASE_DIR / "data" / "logs" / "anomaly_check.log"
DEFAULT_PIPELINE_FAILURE_LOG_PATH = BASE_DIR / "data" / "logs" / "pipeline_failures.log"
SCHEMA_VERSION = "1.0"

SEVERITY_PRIORITY = {
    "ok": 0,
    "info": 1,
    "review": 2,
    "warning": 3,
    "critical": 4,
}


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


def _alert(severity: str, source: str, title: str, message: str, action: str) -> dict[str, Any]:
    return {
        "severity": severity,
        "source": source,
        "title": title,
        "message": message,
        "action": action,
    }


def _read_retry_counts() -> Counter[str]:
    rows = list_queue_items()
    return Counter(str(row.get("retry_status", "unknown")) for row in rows)


def _anomaly_alerts(status_light: dict[str, Any], anomaly_log_text: str) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []

    overall = str(status_light.get("anomaly_overall") or "N/A").strip().upper()
    if overall in {"CRITICAL", "FAIL"}:
        alerts.append(
            _alert(
                "critical",
                "anomaly",
                "Anomaly Critical",
                f"anomaly overall is {overall}",
                "anomaly_check.log と daily_report を確認",
            )
        )
    elif overall in {"WARNING", "REVIEW"}:
        alerts.append(
            _alert(
                "warning",
                "anomaly",
                "Anomaly Warning",
                f"anomaly overall is {overall}",
                "daily_report と release_readiness を確認",
            )
        )
    elif overall in {"OK", "PASS", "RELEASE"}:
        alerts.append(
            _alert(
                "info",
                "anomaly",
                "Anomaly Status OK",
                "anomaly overall is stable",
                "定期監視を継続",
            )
        )

    if anomaly_log_text:
        line_count = len([line for line in anomaly_log_text.splitlines() if line.strip()])
        if line_count > 0 and overall == "N/A":
            alerts.append(
                _alert(
                    "info",
                    "anomaly",
                    "Anomaly Log Available",
                    f"anomaly_check.log has {line_count} lines",
                    "必要に応じて最新ログを確認",
                )
            )

    return alerts


def _readiness_alerts(readiness: dict[str, Any]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []

    decision = str(readiness.get("decision") or "N/A").strip().lower()
    if decision in {"hold", "block", "critical"}:
        alerts.append(
            _alert(
                "critical",
                "readiness",
                "Release Decision Hold",
                f"release readiness decision is {decision}",
                "release_readiness_latest.json の reasons を確認",
            )
        )
    elif decision in {"review", "warning"}:
        alerts.append(
            _alert(
                "review",
                "readiness",
                "Release Decision Review",
                f"release readiness decision is {decision}",
                "recommended_action を確認してレビュー",
            )
        )
    elif decision in {"release", "ok", "pass"}:
        alerts.append(
            _alert(
                "info",
                "readiness",
                "Release Decision Release",
                "release readiness decision is release",
                "通常運用を継続",
            )
        )

    retry_queued = int(readiness.get("retry_queued") or 0)
    if retry_queued > 0:
        alerts.append(
            _alert(
                "warning",
                "readiness",
                "Retry Queue Pending",
                f"retry_queued is {retry_queued}",
                "retry queue の滞留要因を確認",
            )
        )

    return alerts


def _retry_alerts(retry_counts: Counter[str]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []

    queued = int(retry_counts.get("queued", 0))
    retrying = int(retry_counts.get("retrying", 0))
    give_up = int(retry_counts.get("give_up", 0))

    if give_up > 0:
        alerts.append(
            _alert(
                "critical",
                "retry_queue",
                "Retry Queue Give Up",
                f"give_up items exist: {give_up}",
                "give_up item の last_error を確認し手動対応",
            )
        )

    if queued > 0 or retrying > 0:
        alerts.append(
            _alert(
                "warning",
                "retry_queue",
                "Retry Queue Active",
                f"queued={queued}, retrying={retrying}",
                "再試行キューの進行状況を確認",
            )
        )
    else:
        alerts.append(
            _alert(
                "info",
                "retry_queue",
                "Retry Queue Empty",
                "retry queue has no pending items",
                "監視のみ継続",
            )
        )

    return alerts


def _failure_alerts(pipeline_failure_log_text: str) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []

    lines = [line for line in pipeline_failure_log_text.splitlines() if line.strip()]
    if not lines:
        alerts.append(
            _alert(
                "info",
                "pipeline_failure",
                "Pipeline Failure Log Empty",
                "pipeline failure log has no recent entries",
                "監視のみ継続",
            )
        )
        return alerts

    error_count = sum(1 for line in lines if "| ERROR |" in line)
    warning_count = sum(1 for line in lines if "| WARNING |" in line)

    if error_count > 0:
        alerts.append(
            _alert(
                "critical",
                "pipeline_failure",
                "Pipeline Error Detected",
                f"pipeline failure log contains ERROR lines: {error_count}",
                "pipeline_failures.log の最新エントリを確認",
            )
        )
    elif warning_count > 0:
        alerts.append(
            _alert(
                "warning",
                "pipeline_failure",
                "Pipeline Warning Detected",
                f"pipeline failure log contains WARNING lines: {warning_count}",
                "warning 内容と通知設定を確認",
            )
        )
    else:
        alerts.append(
            _alert(
                "info",
                "pipeline_failure",
                "Pipeline Log Present",
                f"pipeline failure log has {len(lines)} lines",
                "必要に応じてログ詳細を確認",
            )
        )

    return alerts


def _compute_overall(alerts: list[dict[str, Any]]) -> str:
    if not alerts:
        return "ok"

    highest = 0
    for alert in alerts:
        severity = str(alert.get("severity") or "info").lower()
        highest = max(highest, SEVERITY_PRIORITY.get(severity, 1))

    if highest >= SEVERITY_PRIORITY["critical"]:
        return "critical"
    if highest >= SEVERITY_PRIORITY["warning"]:
        return "warning"
    if highest >= SEVERITY_PRIORITY["review"]:
        return "review"
    return "ok"


def build_ops_alert_center() -> dict[str, Any]:
    status_light = _safe_read_json(DEFAULT_STATUS_LIGHT_JSON_PATH)
    readiness = _safe_read_json(DEFAULT_RELEASE_READINESS_JSON_PATH)
    anomaly_log_text = _safe_read_text(DEFAULT_ANOMALY_LOG_PATH)
    pipeline_failure_log_text = _safe_read_text(DEFAULT_PIPELINE_FAILURE_LOG_PATH)
    retry_counts = _read_retry_counts()

    alerts: list[dict[str, Any]] = []
    alerts.extend(_anomaly_alerts(status_light, anomaly_log_text))
    alerts.extend(_readiness_alerts(readiness))
    alerts.extend(_retry_alerts(retry_counts))
    alerts.extend(_failure_alerts(pipeline_failure_log_text))

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "overall": _compute_overall(alerts),
        "alerts": alerts,
        "summary": {
            "alert_count": len(alerts),
            "critical_count": sum(1 for alert in alerts if alert.get("severity") == "critical"),
            "warning_count": sum(1 for alert in alerts if alert.get("severity") == "warning"),
            "review_count": sum(1 for alert in alerts if alert.get("severity") == "review"),
            "info_count": sum(1 for alert in alerts if alert.get("severity") == "info"),
        },
        "signals": {
            "retry_queue": {
                "queued": int(retry_counts.get("queued", 0)),
                "retrying": int(retry_counts.get("retrying", 0)),
                "resolved": int(retry_counts.get("resolved", 0)),
                "give_up": int(retry_counts.get("give_up", 0)),
            },
            "status_light": {
                "decision": status_light.get("decision"),
                "anomaly_overall": status_light.get("anomaly_overall"),
            },
            "release_readiness": {
                "decision": readiness.get("decision"),
                "retry_queued": readiness.get("retry_queued"),
            },
        },
        "sources": {
            "status_light": {
                "path": _normalize_path(DEFAULT_STATUS_LIGHT_JSON_PATH),
                "exists": DEFAULT_STATUS_LIGHT_JSON_PATH.exists(),
            },
            "release_readiness": {
                "path": _normalize_path(DEFAULT_RELEASE_READINESS_JSON_PATH),
                "exists": DEFAULT_RELEASE_READINESS_JSON_PATH.exists(),
            },
            "anomaly_log": {
                "path": _normalize_path(DEFAULT_ANOMALY_LOG_PATH),
                "exists": DEFAULT_ANOMALY_LOG_PATH.exists(),
            },
            "pipeline_failure_log": {
                "path": _normalize_path(DEFAULT_PIPELINE_FAILURE_LOG_PATH),
                "exists": DEFAULT_PIPELINE_FAILURE_LOG_PATH.exists(),
            },
        },
        "status": {
            "fail_safe": True,
        },
    }