"""Auto FREEZE judge for Phase2 governance.

Evaluates KPI values and returns CONTINUE / WARN / FREEZE with reasons.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

FREEZE_THRESHOLDS = {
    "failsafe_coverage_min": 1.00,
    "freeze_correctness_min": 0.90,
    "policy_deny_delta_max": 2.0,
    "warning_streak_freeze": 2,
}

WARN_THRESHOLDS = {
    "freeze_correctness_min": 0.95,
    "policy_deny_delta_max": 1.5,
    "warning_streak_warn": 1,
}


class FreezeDecision(str, Enum):
    CONTINUE = "CONTINUE"
    WARN = "WARN"
    FREEZE = "FREEZE"


@dataclass
class FreezeJudgeResult:
    decision: FreezeDecision
    reasons: list[str]
    normalized_kpi: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reasons": self.reasons,
            "normalized_kpi": self.normalized_kpi,
        }


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def normalize_kpi(kpi: dict[str, Any] | None) -> dict[str, Any]:
    src = kpi if isinstance(kpi, dict) else {}
    return {
        "failsafe_coverage": _safe_float(src.get("failsafe_coverage"), 0.0),
        "freeze_correctness": _safe_float(src.get("freeze_correctness"), 0.0),
        "policy_deny_delta": _safe_float(src.get("policy_deny_delta"), 0.0),
        "warning_streak": _safe_int(src.get("warning_streak"), 0),
    }


def _freeze_reasons(kpi: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if kpi["failsafe_coverage"] < FREEZE_THRESHOLDS["failsafe_coverage_min"]:
        reasons.append(
            f"failsafe_coverage<{FREEZE_THRESHOLDS['failsafe_coverage_min']:.2f} ({kpi['failsafe_coverage']:.4f})"
        )
    if kpi["freeze_correctness"] < FREEZE_THRESHOLDS["freeze_correctness_min"]:
        reasons.append(
            f"freeze_correctness<{FREEZE_THRESHOLDS['freeze_correctness_min']:.2f} ({kpi['freeze_correctness']:.4f})"
        )
    if kpi["policy_deny_delta"] >= FREEZE_THRESHOLDS["policy_deny_delta_max"]:
        reasons.append(
            f"policy_deny_delta>={FREEZE_THRESHOLDS['policy_deny_delta_max']:.1f} ({kpi['policy_deny_delta']:.4f})"
        )
    if kpi["warning_streak"] >= FREEZE_THRESHOLDS["warning_streak_freeze"]:
        reasons.append(
            f"warning_streak>={FREEZE_THRESHOLDS['warning_streak_freeze']} ({kpi['warning_streak']})"
        )
    return reasons


def _warn_reasons(kpi: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if kpi["freeze_correctness"] < WARN_THRESHOLDS["freeze_correctness_min"]:
        reasons.append(
            f"freeze_correctness<{WARN_THRESHOLDS['freeze_correctness_min']:.2f} ({kpi['freeze_correctness']:.4f})"
        )
    if kpi["policy_deny_delta"] >= WARN_THRESHOLDS["policy_deny_delta_max"]:
        reasons.append(
            f"policy_deny_delta>={WARN_THRESHOLDS['policy_deny_delta_max']:.1f} ({kpi['policy_deny_delta']:.4f})"
        )
    if kpi["warning_streak"] >= WARN_THRESHOLDS["warning_streak_warn"]:
        reasons.append(
            f"warning_streak>={WARN_THRESHOLDS['warning_streak_warn']} ({kpi['warning_streak']})"
        )
    return reasons


def judge_auto_freeze(kpi: dict[str, Any] | None) -> FreezeJudgeResult:
    """Return CONTINUE / WARN / FREEZE based on Phase2 KPI values.

    FREEZE rules:
    - failsafe_coverage < 1.00
    - freeze_correctness < 0.90
    - policy_deny_delta >= 2.0
    - warning_streak >= 2

    WARN is returned only when FREEZE does not trigger and at least one warn
    condition matches.
    """
    nkpi = normalize_kpi(kpi)
    freeze_reasons = _freeze_reasons(nkpi)
    if freeze_reasons:
        return FreezeJudgeResult(
            decision=FreezeDecision.FREEZE,
            reasons=freeze_reasons,
            normalized_kpi=nkpi,
        )

    warn_reasons = _warn_reasons(nkpi)
    if warn_reasons:
        return FreezeJudgeResult(
            decision=FreezeDecision.WARN,
            reasons=warn_reasons,
            normalized_kpi=nkpi,
        )

    return FreezeJudgeResult(
        decision=FreezeDecision.CONTINUE,
        reasons=[],
        normalized_kpi=nkpi,
    )
