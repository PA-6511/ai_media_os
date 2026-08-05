from __future__ import annotations


def judge_phase22_readiness(validation_result: dict, policy_result: dict) -> dict:
    if (
        validation_result.get("status") == "PASS"
        and policy_result.get("policy_status") == "PASS"
    ):
        return {
            "readiness_status": "READY_FOR_PHASE22_PLANNING_ONLY",
            "can_apply": False,
            "next_step": "prepare_phase22_manual_approval_design",
        }

    return {
        "readiness_status": "NOT_READY",
        "can_apply": False,
        "next_step": "fix_phase21_findings",
    }
