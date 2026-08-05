from __future__ import annotations


def judge_phase27_planning_readiness(policy_result: dict) -> dict:
    if policy_result.get("policy_status") == "PASS":
        return {
            "readiness_status": "READY_FOR_PHASE27_PLANNING_ONLY",
            "can_execute": False,
            "next_step": "prepare_phase27_manual_dry_run_go_no_go_design",
        }

    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase26_findings",
    }
