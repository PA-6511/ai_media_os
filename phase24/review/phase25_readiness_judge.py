from __future__ import annotations


def judge_phase25_planning_readiness(
    validation_result: dict,
    policy_result: dict,
    selected_decision: str | None = None,
) -> dict:
    if (
        validation_result.get("status") == "PASS"
        and policy_result.get("policy_status") == "PASS"
        and selected_decision == "GO_PHASE25_PLANNING_ONLY"
    ):
        return {
            "readiness_status": "READY_FOR_PHASE25_PLANNING_ONLY",
            "can_execute": False,
            "next_step": "prepare_phase25_manual_approval_dry_run_execution_plan",
        }

    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase24_findings_or_no_go",
    }
