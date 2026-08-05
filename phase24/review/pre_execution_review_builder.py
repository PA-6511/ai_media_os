from __future__ import annotations


def build_pre_execution_review(phase23_result: dict) -> dict:
    if phase23_result.get("readiness_status") != "READY_FOR_PHASE24_PLANNING_ONLY":
        return {
            "status": "FAIL",
            "reason": "phase23_not_ready_for_phase24_planning_only",
        }

    if phase23_result.get("can_execute") is not False:
        return {
            "status": "FAIL",
            "reason": "phase23_can_execute_must_be_false",
        }

    return {
        "phase": "24",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "review_scope": "single_file_pre_execution_review_only",
        "max_files_to_execute": 1,
        "execute_allowed": False,
        "status": "PRE_EXECUTION_REVIEW_READY",
        "checklist_items": [
            "confirm_single_file_limit",
            "confirm_dry_run_mode",
            "confirm_manual_approval_required",
            "confirm_stop_conditions_defined",
        ],
        "stop_conditions_confirmed": True,
        "next_step": "design_go_nogo_decision",
    }
