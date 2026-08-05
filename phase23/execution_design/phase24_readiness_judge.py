from __future__ import annotations


def judge_phase24_planning_readiness(policy_result: dict) -> dict:
    if policy_result.get("policy_status") == "PASS":
        return {
            "readiness_status": "READY_FOR_PHASE24_PLANNING_ONLY",
            "can_execute": False,
            "next_step": "prepare_phase24_pre_execution_review",
        }

    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase23_findings",
    }
