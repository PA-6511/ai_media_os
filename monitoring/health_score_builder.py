from __future__ import annotations

from typing import Any


def score_to_grade(score: int) -> str:
    """数値スコアをグレード文字列に変換する。"""
    s = int(score)
    if s >= 90:
        return "A"
    if s >= 75:
        return "B"
    if s >= 60:
        return "C"
    if s >= 40:
        return "D"
    return "E"


def build_health_score(summary: dict) -> dict[str, Any]:
    """recovery summary を受け取り health_score / grade / 減点根拠を返す。

    採点ルール（減点式、初期値 100）:
    - anomaly overall = WARNING    → -20
    - anomaly overall = CRITICAL   → -50
    - smoke_test failed 1件ごとに  → -10
    - retry queued > 0             → -10
    - latest archive が無い        → -10
    - latest dashboard が無い      → -10
    - failed_count >= 1            → -10
    - failed_count >= 3            → さらに -10
    """
    anomaly = summary.get("anomaly") or {}
    retry = summary.get("retry_queue") or {}
    artifacts = summary.get("artifacts") or {}

    anomaly_overall = str(anomaly.get("overall", "UNKNOWN"))
    smoke_failed_count = int(anomaly.get("smoke_failed_count", 0))
    failed_count = int(anomaly.get("failed_count", 0))
    queued = int(retry.get("queued", 0))
    latest_archive = artifacts.get("latest_archive")
    latest_dashboard = artifacts.get("latest_dashboard")

    score = 100
    deductions: list[dict[str, Any]] = []

    if anomaly_overall == "WARNING":
        score -= 20
        deductions.append({"reason": "anomaly overall=WARNING", "deduction": -20})
    elif anomaly_overall == "CRITICAL":
        score -= 50
        deductions.append({"reason": "anomaly overall=CRITICAL", "deduction": -50})

    if smoke_failed_count > 0:
        d = smoke_failed_count * 10
        score -= d
        deductions.append({"reason": f"smoke_test failed x{smoke_failed_count}", "deduction": -d})

    if queued > 0:
        score -= 10
        deductions.append({"reason": f"retry_queue queued={queued}", "deduction": -10})

    if not latest_archive:
        score -= 10
        deductions.append({"reason": "no latest archive", "deduction": -10})

    if not latest_dashboard:
        score -= 10
        deductions.append({"reason": "no latest dashboard", "deduction": -10})

    if failed_count >= 1:
        score -= 10
        deductions.append({"reason": f"failed_count >= 1 (value={failed_count})", "deduction": -10})

    if failed_count >= 3:
        score -= 10
        deductions.append({"reason": f"failed_count >= 3 (value={failed_count})", "deduction": -10})

    score = max(0, score)
    grade = score_to_grade(score)

    return {
        "score": score,
        "grade": grade,
        "deductions": deductions,
        "inputs": {
            "anomaly_overall": anomaly_overall,
            "smoke_failed_count": smoke_failed_count,
            "failed_count": failed_count,
            "retry_queued": queued,
            "has_latest_archive": bool(latest_archive),
            "has_latest_dashboard": bool(latest_dashboard),
        },
    }
