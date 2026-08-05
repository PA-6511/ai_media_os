from __future__ import annotations


def judge_phase69_planning_readiness(
    policy_result: dict,
    selected_decision: str | None = None,
) -> dict:
    if (
        policy_result.get("policy_status") == "PASS"
        and selected_decision == "ALLOW_PHASE69_PLANNING_ONLY"
    ):
        return {
            "readiness_status": "READY_FOR_PHASE69_PLANNING_ONLY",
            "can_execute": False,
            "execute_allowed": False,
            "next_step": "prepare_phase69_limited_dry_run_preparation_review",
        }
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "execute_allowed": False,
        "next_step": "fix_phase68_findings_or_reject",
    }
