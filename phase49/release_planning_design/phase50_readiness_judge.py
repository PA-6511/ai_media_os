from __future__ import annotations


def judge_phase50_planning_readiness(
    policy_result: dict,
    selected_decision: str | None = None,
) -> dict:
    if (
        policy_result.get("policy_status") == "PASS"
        and selected_decision == "ALLOW_PHASE50_PLANNING_ONLY"
    ):
        return {
            "readiness_status": "READY_FOR_PHASE50_PLANNING_ONLY",
            "can_execute": False,
            "next_step": "prepare_phase50_manual_dry_run_execution_cutover_planning_package_design",
        }
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase49_findings_or_reject",
    }
