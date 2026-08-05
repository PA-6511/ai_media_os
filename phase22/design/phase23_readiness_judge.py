from __future__ import annotations


def judge_phase23_planning_readiness(policy_result: dict) -> dict:
    if policy_result.get("policy_status") == "PASS":
        return {
            "readiness_status": "READY_FOR_PHASE23_PLANNING_ONLY",
            "can_apply": False,
            "next_step": "prepare_phase23_controlled_execution_design",
        }

    return {
        "readiness_status": "NOT_READY",
        "can_apply": False,
        "next_step": "fix_phase22_findings",
    }
