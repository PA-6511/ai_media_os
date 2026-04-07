from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from monitoring.kpi_snapshot_reader import extract_kpi_summary, load_latest_kpi_snapshot
from ops.recovery_summary_builder import build_recovery_summary


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_RELEASE_READINESS_PATH = BASE_DIR / "data" / "reports" / "release_readiness_latest.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def check_exists(path_str: str | None) -> bool:
    if not path_str:
        return False
    return Path(path_str).exists()


def _safe_get(mapping: dict[str, Any] | None, key: str, default: Any) -> Any:
    if not isinstance(mapping, dict):
        return default
    return mapping.get(key, default)


def load_latest_release_readiness(path: Path | None = None) -> dict | None:
    """最新 release readiness JSON を読み込む。無い場合は None。"""
    target = path or DEFAULT_RELEASE_READINESS_PATH
    if not target.exists() or not target.is_file():
        return None

    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return None

    return payload if isinstance(payload, dict) else None


def summarize_release_readiness(summary: dict | None) -> dict[str, Any]:
    """checklist表示用に release readiness を短く要約する。"""
    if not summary:
        return {
            "release_decision": "N/A",
            "release_reasons": [],
            "recommended_action": "N/A",
        }

    reasons_raw = summary.get("reasons") if isinstance(summary.get("reasons"), list) else []
    reasons = [str(r) for r in reasons_raw if str(r).strip()][:3]

    return {
        "release_decision": str(summary.get("decision", "N/A")),
        "release_reasons": reasons,
        "recommended_action": str(summary.get("recommended_action", "N/A")),
    }


def collect_daily_checklist_context() -> dict[str, Any]:
    """daily checklist 生成に必要な recovery 情報を集める。"""
    try:
        summary = build_recovery_summary()
    except Exception as exc:  # noqa: BLE001
        summary = {
            "generated_at": _now_iso(),
            "anomaly": {
                "overall": "N/A",
                "alert_count": 0,
                "warning_count": 0,
                "critical_count": 0,
                "error": str(exc),
            },
            "health_score": {"score": "N/A", "grade": "N/A"},
            "retry_queue": {"queued": 0},
            "latest_daily_report": None,
            "latest_dashboard": None,
            "latest_archive": None,
            "next_actions": ["recovery summary を取得できませんでした"],
        }

    anomaly = _safe_get(summary, "anomaly", {})
    health = _safe_get(summary, "health_score", {})
    retry = _safe_get(summary, "retry_queue", {})
    next_actions = summary.get("next_actions") if isinstance(summary, dict) else []
    next_action = next_actions[0] if isinstance(next_actions, list) and next_actions else "N/A"

    latest_daily_report = summary.get("latest_daily_report") if isinstance(summary, dict) else None
    latest_dashboard = summary.get("latest_dashboard") if isinstance(summary, dict) else None
    latest_archive = summary.get("latest_archive") if isinstance(summary, dict) else None

    kpi = extract_kpi_summary(load_latest_kpi_snapshot())
    kpi_anomaly = kpi.get("anomaly_overall")
    kpi_health_score = kpi.get("health_score")
    kpi_health_grade = kpi.get("health_grade")
    kpi_archive = kpi.get("latest_archive")
    kpi_retry = int(kpi.get("retry_queued_count", 0) or 0)

    anomaly_overall = kpi_anomaly if kpi_anomaly not in (None, "N/A") else _safe_get(anomaly, "overall", "N/A")
    health_score = kpi_health_score if kpi_health_score not in (None, "N/A") else _safe_get(health, "score", "N/A")
    health_grade = kpi_health_grade if kpi_health_grade not in (None, "N/A") else _safe_get(health, "grade", "N/A")
    archive_path = kpi_archive or latest_archive
    retry_queued_count = kpi_retry if kpi_retry >= 0 else int(_safe_get(retry, "queued", 0) or 0)
    release_readiness = summarize_release_readiness(load_latest_release_readiness())

    return {
        "generated_at": summary.get("generated_at", _now_iso()) if isinstance(summary, dict) else _now_iso(),
        "anomaly_overall": anomaly_overall,
        "alert_count": int(_safe_get(anomaly, "alert_count", 0) or 0),
        "warning_count": int(_safe_get(anomaly, "warning_count", 0) or 0),
        "critical_count": int(_safe_get(anomaly, "critical_count", 0) or 0),
        "health_score": health_score,
        "health_grade": health_grade,
        "retry_queued_count": retry_queued_count,
        "latest_daily_report": latest_daily_report or "未検出",
        "latest_dashboard": latest_dashboard or "未検出",
        "latest_archive": archive_path or "未検出",
        "next_action": next_action,
        "daily_report_exists": check_exists(latest_daily_report),
        "dashboard_exists": check_exists(latest_dashboard),
        "archive_exists": check_exists(archive_path),
        "kpi_summary": kpi,
        "release_decision": release_readiness.get("release_decision", "N/A"),
        "release_reasons": release_readiness.get("release_reasons", []),
        "recommended_action": release_readiness.get("recommended_action", "N/A"),
    }


def build_daily_checklist_markdown() -> str:
    """定常確認用 daily checklist Markdown を生成する。"""
    context = collect_daily_checklist_context()

    lines: list[str] = []
    lines.append("# AI Media OS Daily Checklist")
    lines.append("")
    lines.append(f"generated_at: {context['generated_at']}")
    lines.append("")
    lines.append(f"anomaly: {context['anomaly_overall']}")
    lines.append(
        "alerts: "
        f"total={context['alert_count']} "
        f"warning={context['warning_count']} "
        f"critical={context['critical_count']}"
    )
    lines.append(f"health_score: {context['health_score']} ({context['health_grade']})")
    lines.append(f"retry_queued: {context['retry_queued_count']}")
    lines.append(f"latest_daily_report: {context['latest_daily_report']}")
    lines.append(f"latest_dashboard: {context['latest_dashboard']}")
    lines.append(f"latest_archive: {context['latest_archive']}")
    lines.append(f"next_action: {context['next_action']}")
    lines.append("")
    lines.append(f"release_decision: {context['release_decision']}")
    lines.append("release_reasons:")
    release_reasons = context.get("release_reasons") or []
    if release_reasons:
        for reason in release_reasons[:3]:
            lines.append(f"- {reason}")
    else:
        lines.append("- N/A")
    lines.append(f"recommended_action: {context['recommended_action']}")
    lines.append("")
    lines.append("## Check Items")
    lines.append("")
    lines.append(f"- anomaly が OK: {'YES' if context['anomaly_overall'] == 'OK' else 'NO'}")
    lines.append(f"- retry queue が 0: {'YES' if context['retry_queued_count'] == 0 else 'NO'}")
    lines.append(f"- daily report が存在: {'YES' if context['daily_report_exists'] else 'NO'}")
    lines.append(f"- dashboard が存在: {'YES' if context['dashboard_exists'] else 'NO'}")
    lines.append(f"- archive が存在: {'YES' if context['archive_exists'] else 'NO'}")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"