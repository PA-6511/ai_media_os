from __future__ import annotations


def judge_phase60_planning_readiness(
    policy_result: dict,
    selected_decision: str | None = None,
) -> dict:
    if (
        policy_result.get("policy_status") == "PASS"
        and selected_decision == "ALLOW_PHASE60_PLANNING_ONLY"
    ):
        return {
            "readiness_status": "READY_FOR_PHASE60_PLANNING_ONLY",
            "can_execute": False,
            "next_step": "prepare_phase60_manual_dry_run_execution_operational_readiness_package_design",
        }
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase59_findings_or_reject",
    }
