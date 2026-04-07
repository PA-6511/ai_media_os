from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from monitoring.kpi_snapshot_reader import load_kpi_snapshots
from ops.release_readiness_history_reader import load_release_readiness_history
from reporting.artifact_index_builder import DEFAULT_REPORT_DIR


DEFAULT_OPS_API_PAYLOAD_JSON_PATH = DEFAULT_REPORT_DIR / "ops_api_payload_latest.json"
DEFAULT_STATUS_BADGE_JSON_PATH = DEFAULT_REPORT_DIR / "status_badge_latest.json"
DEFAULT_RELEASE_READINESS_JSON_PATH = DEFAULT_REPORT_DIR / "release_readiness_latest.json"
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


def _normalize_decision(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "N/A"
    return text.upper()


def _str_or_na(value: Any) -> str:
    text = str(value).strip() if value is not None else ""
    return text if text else "N/A"


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def load_recent_release_decisions(limit: int = 3) -> list[str]:
    """release readiness 履歴から直近判定を新しい順で返す。"""
    rows = load_release_readiness_history(limit=limit)
    decisions: list[str] = []

    for row in rows:
        value = str((row or {}).get("decision") or "").strip().lower()
        decisions.append(value if value else "n/a")

    return decisions


def load_recent_kpi_scores(limit: int = 3) -> dict[str, list[Any]]:
    """KPI スナップショット直近値の軽量要約を返す。"""
    rows = load_kpi_snapshots(limit=limit)

    health_scores: list[int | None] = []
    anomaly_overall: list[str] = []
    health_grades: list[str] = []

    for row in rows:
        health_scores.append(_int_or_none((row or {}).get("health_score")))

        anomaly_text = str((row or {}).get("anomaly_overall") or "").strip().upper()
        anomaly_overall.append(anomaly_text if anomaly_text else "N/A")

        grade_text = str((row or {}).get("health_grade") or "").strip().upper()
        health_grades.append(grade_text if grade_text else "N/A")

    return {
        "health_scores": health_scores,
        "anomaly_overall": anomaly_overall,
        "health_grades": health_grades,
    }


def build_ops_status_light() -> dict[str, Any]:
    ops_api_payload = _safe_read_json(DEFAULT_OPS_API_PAYLOAD_JSON_PATH) or {}
    status_badge = _safe_read_json(DEFAULT_STATUS_BADGE_JSON_PATH) or {}
    release_readiness = _safe_read_json(DEFAULT_RELEASE_READINESS_JSON_PATH) or {}

    compact_summary = ops_api_payload.get("compact_summary")
    compact = compact_summary if isinstance(compact_summary, dict) else {}

    payload_badge = ops_api_payload.get("status_badge")
    payload_badge = payload_badge if isinstance(payload_badge, dict) else {}

    payload_readiness = ops_api_payload.get("release_readiness")
    payload_readiness = payload_readiness if isinstance(payload_readiness, dict) else {}

    payload_summary = ops_api_payload.get("ops_summary")
    payload_summary = payload_summary if isinstance(payload_summary, dict) else {}

    decision = _normalize_decision(
        compact.get("decision")
        or payload_badge.get("decision")
        or status_badge.get("decision")
        or payload_readiness.get("decision")
        or release_readiness.get("decision")
    )

    badge_text = _str_or_na(
        compact.get("badge_text")
        or payload_badge.get("badge_text")
        or status_badge.get("badge_text")
    )

    health_score = _int_or_none(
        compact.get("health_score")
        if compact.get("health_score") is not None
        else payload_badge.get("health_score")
        if payload_badge.get("health_score") is not None
        else status_badge.get("health_score")
        if status_badge.get("health_score") is not None
        else payload_readiness.get("health_score")
        if payload_readiness.get("health_score") is not None
        else release_readiness.get("health_score")
    )

    health_grade = _str_or_na(
        compact.get("health_grade")
        or payload_badge.get("health_grade")
        or status_badge.get("health_grade")
        or payload_readiness.get("health_grade")
        or release_readiness.get("health_grade")
    )

    anomaly_overall = _str_or_na(
        compact.get("anomaly_overall")
        or payload_badge.get("anomaly_overall")
        or status_badge.get("anomaly_overall")
        or payload_readiness.get("anomaly_overall")
        or release_readiness.get("anomaly_overall")
    )

    latest_daily_report = _str_or_na(
        payload_readiness.get("latest_daily_report")
        or release_readiness.get("latest_daily_report")
        or payload_summary.get("latest_daily_report_json")
    )

    latest_archive = _str_or_na(
        payload_summary.get("latest_archive")
        or payload_readiness.get("latest_archive")
        or release_readiness.get("latest_archive")
    )

    recommended_action = _str_or_na(
        compact.get("recommended_action")
        or payload_readiness.get("recommended_action")
        or release_readiness.get("recommended_action")
        or payload_summary.get("release_recommended_action")
    )

    recent_release_decisions = load_recent_release_decisions(limit=3)
    recent_kpi = load_recent_kpi_scores(limit=3)

    recent_trend = {
        "release_decisions": recent_release_decisions,
        "health_scores": recent_kpi.get("health_scores", []),
        "anomaly_overall": recent_kpi.get("anomaly_overall", []),
    }

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "decision": decision,
        "badge_text": badge_text,
        "health_score": health_score,
        "health_grade": health_grade,
        "anomaly_overall": anomaly_overall,
        "latest_daily_report": latest_daily_report,
        "latest_archive": latest_archive,
        "recommended_action": recommended_action,
        "recent_trend": recent_trend,
        "source": {
            "ops_api_payload_json": str(DEFAULT_OPS_API_PAYLOAD_JSON_PATH)
            if DEFAULT_OPS_API_PAYLOAD_JSON_PATH.exists()
            else None,
            "status_badge_json": str(DEFAULT_STATUS_BADGE_JSON_PATH)
            if DEFAULT_STATUS_BADGE_JSON_PATH.exists()
            else None,
            "release_readiness_json": str(DEFAULT_RELEASE_READINESS_JSON_PATH)
            if DEFAULT_RELEASE_READINESS_JSON_PATH.exists()
            else None,
        },
    }
