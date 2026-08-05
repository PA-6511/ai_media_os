from __future__ import annotations


def build_phase22_approval_format(phase21_result: dict) -> dict:
    if phase21_result.get("readiness_status") != "READY_FOR_PHASE22_PLANNING_ONLY":
        return {
            "status": "FAIL",
            "reason": "phase21_not_ready_for_phase22_planning_only",
        }

    if phase21_result.get("can_apply") is not False:
        return {
            "status": "FAIL",
            "reason": "phase21_can_apply_must_be_false",
        }

    return {
        "phase": "22",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "approval_required": True,
        "decision_format": [
            "APPROVE_PHASE23_PLANNING_ONLY",
            "REJECT",
            "NEEDS_REVISION",
        ],
        "approve_does_not_apply": True,
        "status": "APPROVAL_FORMAT_READY",
    }
