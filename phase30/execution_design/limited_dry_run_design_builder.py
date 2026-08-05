from __future__ import annotations


def build_limited_dry_run_design(phase29_result: dict) -> dict:
    if phase29_result.get("readiness_status") != "READY_FOR_PHASE30_PLANNING_ONLY":
        return {
            "status": "FAIL",
            "reason": "phase29_not_ready_for_phase30_planning_only",
        }

    if phase29_result.get("can_execute") is not False:
        return {
            "status": "FAIL",
            "reason": "phase29_can_execute_must_be_false",
        }

    return {
        "phase": "30",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "execution_scope": "single_file_sandbox_dry_run_design_only",
        "max_files_to_execute": 1,
        "execute_allowed": False,
        "sandbox_scope_required": True,
        "status": "LIMITED_DRY_RUN_DESIGN_READY",
        "next_step": "define_constraints_and_manual_gate",
    }
