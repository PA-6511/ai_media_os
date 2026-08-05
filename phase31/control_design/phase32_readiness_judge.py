from __future__ import annotations


def judge_phase32_planning_readiness(
    policy_result: dict,
    selected_decision: str | None = None,
) -> dict:
    if (
        policy_result.get("policy_status") == "PASS"
        and selected_decision == "ALLOW_PHASE32_PLANNING_ONLY"
    ):
        return {
            "readiness_status": "READY_FOR_PHASE32_PLANNING_ONLY",
            "can_execute": False,
            "next_step": "prepare_phase32_pre_execution_review_design",
        }

    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase31_findings_or_reject",
    }
