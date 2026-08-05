from __future__ import annotations


def build_manual_dry_run_execution_final_pre_execution_review(
    phase33_result: dict,
) -> dict:
    if phase33_result.get("readiness_status") != "READY_FOR_PHASE34_PLANNING_ONLY":
        return {
            "status": "FAIL",
            "reason": "phase33_not_ready_for_phase34_planning_only",
        }

    if phase33_result.get("can_execute") is not False:
        return {
            "status": "FAIL",
            "reason": "phase33_can_execute_must_be_false",
        }

    return {
        "phase": "34",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "execution_scope": "manual_dry_run_execution_final_pre_execution_review_design_only",
        "max_files_to_execute": 1,
        "can_execute": False,
        "execute_allowed": False,
        "sandbox_scope_required": True,
        "status": "FINAL_PRE_EXECUTION_REVIEW_READY",
        "next_step": "define_final_review_controls_stop_and_evidence_requirements",
    }
