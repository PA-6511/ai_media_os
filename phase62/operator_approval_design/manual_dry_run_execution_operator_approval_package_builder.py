from __future__ import annotations


def build_manual_dry_run_execution_operator_approval_package(phase61_result: dict) -> dict:
    if phase61_result.get("readiness_status") != "READY_FOR_PHASE62_PLANNING_ONLY":
        return {"status": "FAIL", "reason": "phase61_readiness_status_not_met"}
    if phase61_result.get("can_execute") is not False:
        return {"status": "FAIL", "reason": "phase61_can_execute_must_be_false"}
    return {
        "phase": 62,
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "package_scope": "manual_dry_run_execution_operator_approval_package_design_only",
        "max_files_to_execute": 1,
        "can_execute": False,
        "execute_allowed": False,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "status": "OPERATOR_APPROVAL_PACKAGE_READY",
        "next_step": "build_operator_approval_controls",
    }
