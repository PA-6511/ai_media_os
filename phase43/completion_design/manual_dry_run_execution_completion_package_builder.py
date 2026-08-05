from __future__ import annotations


def build_manual_dry_run_execution_completion_package(phase42_result: dict) -> dict:
    if phase42_result.get("readiness_status") != "READY_FOR_PHASE43_PLANNING_ONLY":
        return {"status": "FAIL", "reason": "phase42_readiness_status_not_met"}
    if phase42_result.get("can_execute") is not False:
        return {"status": "FAIL", "reason": "phase42_can_execute_must_be_false"}
    return {
        "phase": 43,
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "package_scope": "manual_dry_run_execution_completion_package_design_only",
        "max_files_to_execute": 1,
        "can_execute": False,
        "execute_allowed": False,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "status": "COMPLETION_PACKAGE_READY",
        "next_step": "build_completion_controls",
    }
