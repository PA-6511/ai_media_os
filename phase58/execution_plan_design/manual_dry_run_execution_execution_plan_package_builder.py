from __future__ import annotations


def build_manual_dry_run_execution_execution_plan_package(phase57_result: dict) -> dict:
    if phase57_result.get("readiness_status") != "READY_FOR_PHASE58_PLANNING_ONLY":
        return {"status": "FAIL", "reason": "phase57_readiness_status_not_met"}
    if phase57_result.get("can_execute") is not False:
        return {"status": "FAIL", "reason": "phase57_can_execute_must_be_false"}
    return {
        "phase": 58,
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "package_scope": "manual_dry_run_execution_execution_plan_package_design_only",
        "max_files_to_execute": 1,
        "can_execute": False,
        "execute_allowed": False,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "status": "EXECUTION_PLAN_PACKAGE_READY",
        "next_step": "build_execution_plan_controls",
    }
