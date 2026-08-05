from __future__ import annotations


def build_manual_dry_run_execution_final_check_package(phase56_result: dict) -> dict:
    if phase56_result.get("readiness_status") != "READY_FOR_PHASE57_PLANNING_ONLY":
        return {"status": "FAIL", "reason": "phase56_readiness_status_not_met"}
    if phase56_result.get("can_execute") is not False:
        return {"status": "FAIL", "reason": "phase56_can_execute_must_be_false"}
    return {
        "phase": 57,
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "package_scope": "manual_dry_run_execution_final_check_package_design_only",
        "max_files_to_execute": 1,
        "can_execute": False,
        "execute_allowed": False,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "status": "FINAL_CHECK_PACKAGE_READY",
        "next_step": "build_final_check_controls",
    }
