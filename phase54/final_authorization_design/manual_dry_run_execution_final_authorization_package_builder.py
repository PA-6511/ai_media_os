from __future__ import annotations


def build_manual_dry_run_execution_final_authorization_package(phase53_result: dict) -> dict:
    if phase53_result.get("readiness_status") != "READY_FOR_PHASE54_PLANNING_ONLY":
        return {"status": "FAIL", "reason": "phase53_readiness_status_not_met"}
    if phase53_result.get("can_execute") is not False:
        return {"status": "FAIL", "reason": "phase53_can_execute_must_be_false"}
    return {
        "phase": 54,
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "package_scope": "manual_dry_run_execution_final_authorization_package_design_only",
        "max_files_to_execute": 1,
        "can_execute": False,
        "execute_allowed": False,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "status": "FINAL_AUTHORIZATION_PACKAGE_READY",
        "next_step": "build_final_authorization_controls",
    }
