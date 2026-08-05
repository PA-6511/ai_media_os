"""Phase40 → Phase41 readiness judge.

can_execute is always False.
"""
from __future__ import annotations

from typing import Any


def judge_phase41_planning_readiness(
    policy_result: dict[str, Any],
    selected_decision: str,
) -> dict[str, Any]:
    if (
        policy_result.get("policy_status") == "PASS"
        and selected_decision == "ALLOW_PHASE41_PLANNING_ONLY"
    ):
        return {
            "readiness_status": "READY_FOR_PHASE41_PLANNING_ONLY",
            "can_execute": False,
            "next_step": "proceed_to_phase41_planning_only",
        }
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase40_findings_or_reject",
    }
