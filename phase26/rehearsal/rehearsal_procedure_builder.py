from __future__ import annotations


def build_rehearsal_procedure(phase25_result: dict) -> dict:
    if phase25_result.get("readiness_status") != "READY_FOR_PHASE26_PLANNING_ONLY":
        return {
            "status": "FAIL",
            "reason": "phase25_not_ready_for_phase26_planning_only",
        }

    if phase25_result.get("can_execute") is not False:
        return {
            "status": "FAIL",
            "reason": "phase25_can_execute_must_be_false",
        }

    return {
        "phase": "26",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "rehearsal_scope": "single_file_dry_run_rehearsal_only",
        "max_files_to_execute": 1,
        "execute_allowed": False,
        "status": "REHEARSAL_PROCEDURE_READY",
        "steps": [
            "review_manual_approval_package",
            "confirm_single_file_target_scope",
            "verify_abort_conditions_before_rehearsal",
            "prepare_observation_template",
        ],
        "next_step": "define_observation_and_abort_rules",
    }
