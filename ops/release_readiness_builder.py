from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from docs.daily_checklist_builder import collect_daily_checklist_context
from ops.recovery_summary_builder import build_recovery_summary
from reporting.artifact_integrity_checker import run_integrity_checks


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _integrity_has_level(result: dict[str, Any], level: str) -> bool:
    checks = result.get("checks") if isinstance(result, dict) else []
    if not isinstance(checks, list):
        return False
    return any(str(item.get("level", "")).upper() == level for item in checks if isinstance(item, dict))


def _recommended_action(decision: str, reasons: list[str]) -> str:
    if decision == "release":
        has_warning = any("WARNING" in reason for reason in reasons)
        if has_warning:
            return "リリース可。軽微警告を運用監視に登録し、次回 ops cycle で再確認"
        return "通常リリースを許可。定常監視を継続"

    if decision == "review":
        return (
            "担当者レビューを実施し、anomaly/integrity の WARNING 項目を確認後に再判定"
        )

    return (
        "リリース保留。artifact_integrity_check の FAIL・anomaly CRITICAL・retry 残件を"
        "解消後に再判定"
    )


def _to_upper(value: Any, fallback: str = "UNKNOWN") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    if not text:
        return fallback
    return text.upper()


def load_latest_anomaly_summary(recovery: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """最新 anomaly サマリーを返す。recovery を優先利用し、未指定時は再生成する。"""
    base = recovery
    if base is None:
        try:
            base = build_recovery_summary()
        except Exception:  # noqa: BLE001
            return None

    if not isinstance(base, dict):
        return None

    anomaly = base.get("anomaly")
    if not isinstance(anomaly, dict):
        return None

    return {
        "overall": _to_upper(anomaly.get("overall")),
        "alert_total": _to_int(anomaly.get("alert_count"), 0),
        "warning_count": _to_int(anomaly.get("warning_count"), 0),
        "critical_count": _to_int(anomaly.get("critical_count"), 0),
    }


def load_latest_integrity_summary(integrity: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """最新 integrity サマリーを返す。integrity を優先利用し、未指定時は再計算する。"""
    base = integrity
    if base is None:
        try:
            base = run_integrity_checks()
        except Exception:  # noqa: BLE001
            return None

    if not isinstance(base, dict):
        return None

    summary = base.get("summary")
    if not isinstance(summary, dict):
        return None

    return {
        "overall": _to_upper(summary.get("overall")),
        "pass_count": _to_int(summary.get("pass_count"), 0),
        "warning_count": _to_int(summary.get("warning_count"), 0),
        "fail_count": _to_int(summary.get("fail_count"), 0),
    }


def decide_release_readiness(
    *,
    anomaly_overall: str,
    anomaly_alert_total: int,
    anomaly_warning_count: int,
    anomaly_critical_count: int,
    health_score: int,
    retry_queued: int,
    integrity_overall: str,
    integrity_pass_count: int,
    integrity_warning_count: int,
    integrity_fail_count: int,
    integrity_has_warning: bool,
    integrity_has_fail: bool,
) -> dict[str, Any]:
    """判定を release/review/hold で返す。

    Returns:
        {
            "decision": str,
            "reasons": list[str],
            "recommended_action": str,
        }
    """
    hold_reasons: list[str] = []
    review_reasons: list[str] = []

    # HOLD
    if anomaly_overall == "CRITICAL" or anomaly_critical_count > 0:
        hold_reasons.append(
            f"anomaly critical を検知 (critical={anomaly_critical_count})"
        )
    if integrity_overall == "FAIL" or integrity_has_fail or integrity_fail_count > 0:
        hold_reasons.append(
            f"artifact integrity に FAIL がある (fail={integrity_fail_count})"
        )
    if retry_queued > 0:
        hold_reasons.append(f"retry queue が残存 ({retry_queued})")
    if health_score >= 0 and health_score < 60:
        hold_reasons.append(f"health_score が 60 未満 ({health_score})")

    if hold_reasons:
        return {
            "decision": "hold",
            "reasons": hold_reasons,
            "recommended_action": _recommended_action("hold", hold_reasons),
        }

    # REVIEW
    if anomaly_warning_count > 0 and (health_score < 70 or health_score < 0):
        review_reasons.append(
            f"anomaly warning があり health_score が不足 (warning={anomaly_warning_count}, health={health_score})"
        )
    if integrity_overall == "WARNING" or integrity_has_warning or integrity_warning_count > 0:
        review_reasons.append(
            f"artifact integrity に WARNING がある (warning={integrity_warning_count})"
        )
    if 60 <= health_score <= 69:
        review_reasons.append(f"health_score が review 帯 (60-69): {health_score}")

    # RELEASE
    release_allowed = (
        anomaly_overall in {"OK", "WARNING"}
        and anomaly_critical_count == 0
        and retry_queued == 0
        and integrity_fail_count == 0
        and integrity_overall in {"PASS", "WARNING"}
        and health_score >= 70
    )

    warning_release_allowed = (
        release_allowed
        and anomaly_warning_count > 0
        and integrity_warning_count <= 1
        and health_score >= 70
    )

    if release_allowed:
        reasons = [
            "判定条件を満たしたため release",
            (
                "連動指標: "
                f"alerts={anomaly_alert_total} "
                f"warning={anomaly_warning_count} critical={anomaly_critical_count} / "
                f"integrity PASS={integrity_pass_count} WARNING={integrity_warning_count} FAIL={integrity_fail_count}"
            ),
        ]

        if warning_release_allowed:
            reasons.append("WARNING は軽微と判定し、release を維持")

        if anomaly_overall == "WARNING":
            reasons.append("anomaly overall は WARNING だが health/retry/integrity 条件を満たす")

        return {
            "decision": "release",
            "reasons": reasons,
            "recommended_action": _recommended_action("release", reasons),
        }

    if review_reasons:
        review_reasons.append(
            (
                "連動指標: "
                f"alerts={anomaly_alert_total} "
                f"warning={anomaly_warning_count} critical={anomaly_critical_count} / "
                f"integrity PASS={integrity_pass_count} WARNING={integrity_warning_count} FAIL={integrity_fail_count}"
            )
        )
        return {
            "decision": "review",
            "reasons": review_reasons,
            "recommended_action": _recommended_action("review", review_reasons),
        }

    # 境界ケースは review に寄せる
    fallback = [
        "判定条件が不足のため review (境界ケース)",
        (
            "連動指標: "
            f"alerts={anomaly_alert_total} "
            f"warning={anomaly_warning_count} critical={anomaly_critical_count} / "
            f"integrity PASS={integrity_pass_count} WARNING={integrity_warning_count} FAIL={integrity_fail_count}"
        ),
    ]
    return {
        "decision": "review",
        "reasons": fallback,
        "recommended_action": _recommended_action("review", fallback),
    }


def _build_fallback_recovery(error: Exception) -> dict[str, Any]:
    return {
        "generated_at": _now_iso(),
        "anomaly": {"overall": "UNKNOWN"},
        "health_score": {"score": "N/A", "grade": "N/A"},
        "retry_queue": {"queued": 0},
        "latest_daily_report": None,
        "latest_archive": None,
        "error": str(error),
    }


def _build_fallback_integrity(error: Exception) -> dict[str, Any]:
    return {
        "summary": {
            "overall": "UNKNOWN",
            "pass_count": 0,
            "warning_count": 0,
            "fail_count": 0,
        },
        "checks": [],
        "error": str(error),
    }


def _build_fallback_checklist(error: Exception) -> dict[str, Any]:
    return {
        "anomaly_overall": "N/A",
        "retry_queued_count": 0,
        "daily_report_exists": False,
        "dashboard_exists": False,
        "archive_exists": False,
        "error": str(error),
    }


def build_release_readiness() -> dict:
    """運用状態を統合して release/review/hold を判定する。"""
    try:
        recovery = build_recovery_summary()
    except Exception as exc:  # noqa: BLE001
        recovery = _build_fallback_recovery(exc)

    try:
        integrity = run_integrity_checks()
    except Exception as exc:  # noqa: BLE001
        integrity = _build_fallback_integrity(exc)

    try:
        checklist = collect_daily_checklist_context()
    except Exception as exc:  # noqa: BLE001
        checklist = _build_fallback_checklist(exc)

    anomaly = recovery.get("anomaly") if isinstance(recovery, dict) else {}
    health = recovery.get("health_score") if isinstance(recovery, dict) else {}
    retry = recovery.get("retry_queue") if isinstance(recovery, dict) else {}
    anomaly_summary = load_latest_anomaly_summary(recovery) or {}
    integrity_summary = load_latest_integrity_summary(integrity) or {}

    anomaly_overall = str((anomaly or {}).get("overall", "UNKNOWN")).upper()
    anomaly_alert_total = _to_int((anomaly_summary or {}).get("alert_total"), 0)
    anomaly_warning_count = _to_int((anomaly_summary or {}).get("warning_count"), 0)
    anomaly_critical_count = _to_int((anomaly_summary or {}).get("critical_count"), 0)
    health_score = _to_int((health or {}).get("score"), default=-1)
    health_grade = (health or {}).get("grade", "N/A")
    retry_queued = _to_int((retry or {}).get("queued"), default=0)
    integrity_overall = str((integrity_summary or {}).get("overall", "UNKNOWN")).upper()
    integrity_pass_count = _to_int((integrity_summary or {}).get("pass_count"), 0)
    integrity_warning_count = _to_int((integrity_summary or {}).get("warning_count"), 0)
    integrity_fail_count = _to_int((integrity_summary or {}).get("fail_count"), 0)

    integrity_has_warning = _integrity_has_level(integrity, "WARNING")
    integrity_has_fail = _integrity_has_level(integrity, "FAIL")

    decision_result = decide_release_readiness(
        anomaly_overall=anomaly_overall,
        anomaly_alert_total=anomaly_alert_total,
        anomaly_warning_count=anomaly_warning_count,
        anomaly_critical_count=anomaly_critical_count,
        health_score=health_score,
        retry_queued=retry_queued,
        integrity_overall=integrity_overall,
        integrity_pass_count=integrity_pass_count,
        integrity_warning_count=integrity_warning_count,
        integrity_fail_count=integrity_fail_count,
        integrity_has_warning=integrity_has_warning,
        integrity_has_fail=integrity_has_fail,
    )

    decision = str(decision_result.get("decision", "review"))
    reasons = decision_result.get("reasons") if isinstance(decision_result.get("reasons"), list) else []
    recommended_action = str(decision_result.get("recommended_action", _recommended_action(decision, reasons)))

    return {
        "generated_at": _now_iso(),
        "decision": decision,
        "reasons": reasons,
        "anomaly_overall": anomaly_overall,
        "anomaly_alert_total": anomaly_alert_total,
        "anomaly_warning_count": anomaly_warning_count,
        "anomaly_critical_count": anomaly_critical_count,
        "health_score": health_score if health_score >= 0 else "N/A",
        "health_grade": health_grade,
        "retry_queued": retry_queued,
        "integrity_overall": integrity_overall,
        "integrity_pass_count": integrity_pass_count,
        "integrity_warning_count": integrity_warning_count,
        "integrity_fail_count": integrity_fail_count,
        "latest_daily_report": recovery.get("latest_daily_report") if isinstance(recovery, dict) else None,
        "latest_archive": recovery.get("latest_archive") if isinstance(recovery, dict) else None,
        "recommended_action": recommended_action,
        "signals": {
            "checklist_anomaly_overall": checklist.get("anomaly_overall", "N/A"),
            "checklist_retry_queued_count": _to_int(checklist.get("retry_queued_count"), 0),
            "checklist_daily_report_exists": bool(checklist.get("daily_report_exists", False)),
            "checklist_dashboard_exists": bool(checklist.get("dashboard_exists", False)),
            "checklist_archive_exists": bool(checklist.get("archive_exists", False)),
            "integrity_pass_count": integrity_pass_count,
            "integrity_warning_count": integrity_warning_count,
            "integrity_fail_count": integrity_fail_count,
        },
    }
