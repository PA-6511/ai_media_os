from __future__ import annotations


def judge_phase20_readiness(validation_result: dict, policy_result: dict) -> dict:
    if (
        validation_result.get("status") == "PASS"
        and policy_result.get("policy_status") == "PASS"
    ):
        return {
            "readiness_status": "READY_FOR_PHASE21_PLANNING",
            "can_apply": False,
            "next_step": "phase21_controlled_apply_planning",
        }

    return {
        "readiness_status": "NOT_READY",
        "can_apply": False,
        "next_step": "fix_phase20_findings",
    }
