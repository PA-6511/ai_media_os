from __future__ import annotations


def build_manual_dry_run_execution_approval_package(phase32_result: dict) -> dict:
    if phase32_result.get("readiness_status") != "READY_FOR_PHASE33_PLANNING_ONLY":
        return {
            "status": "FAIL",
            "reason": "phase32_not_ready_for_phase33_planning_only",
        }

    if phase32_result.get("can_execute") is not False:
        return {
            "status": "FAIL",
            "reason": "phase32_can_execute_must_be_false",
        }

    return {
        "phase": "33",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "execution_scope": "manual_dry_run_execution_approval_package_design_only",
        "max_files_to_execute": 1,
        "can_execute": False,
        "execute_allowed": False,
        "sandbox_scope_required": True,
        "status": "MANUAL_DRY_RUN_EXECUTION_APPROVAL_PACKAGE_READY",
        "next_step": "define_final_approval_controls_stop_and_evidence_requirements",
    }
