from __future__ import annotations


def build_pre_execution_control_design(phase30_result: dict) -> dict:
    if phase30_result.get("readiness_status") != "READY_FOR_PHASE31_PLANNING_ONLY":
        return {
            "status": "FAIL",
            "reason": "phase30_not_ready_for_phase31_planning_only",
        }

    if phase30_result.get("can_execute") is not False:
        return {
            "status": "FAIL",
            "reason": "phase30_can_execute_must_be_false",
        }

    return {
        "phase": "31",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "execute_allowed": False,
        "can_execute": False,
        "execution_scope": "pre_execution_control_design_only",
        "max_files_to_execute": 1,
        "sandbox_scope_required": True,
        "status": "PRE_EXECUTION_CONTROL_DESIGN_READY",
        "next_step": "define_stop_conditions_and_evidence_requirements",
    }
