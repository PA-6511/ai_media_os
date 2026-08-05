from __future__ import annotations


def judge_phase26_planning_readiness(policy_result: dict) -> dict:
    if policy_result.get("policy_status") == "PASS":
        return {
            "readiness_status": "READY_FOR_PHASE26_PLANNING_ONLY",
            "can_execute": False,
            "next_step": "prepare_phase26_manual_dry_run_rehearsal_design",
        }

    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase25_findings",
    }
