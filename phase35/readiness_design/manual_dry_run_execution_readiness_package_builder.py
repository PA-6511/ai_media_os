from __future__ import annotations


def build_manual_dry_run_execution_readiness_package(phase34_result: dict) -> dict:
    if phase34_result.get("readiness_status") != "READY_FOR_PHASE35_PLANNING_ONLY":
        return {
            "status": "FAIL",
            "reason": "phase34_not_ready_for_phase35_planning_only",
        }

    if phase34_result.get("can_execute") is not False:
        return {
            "status": "FAIL",
            "reason": "phase34_can_execute_must_be_false",
        }

    return {
        "phase": "35",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "execution_scope": "manual_dry_run_execution_readiness_package_design_only",
        "max_files_to_execute": 1,
        "can_execute": False,
        "execute_allowed": False,
        "sandbox_scope_required": True,
        "status": "MANUAL_DRY_RUN_EXECUTION_READINESS_PACKAGE_READY",
        "next_step": "define_readiness_controls_stop_and_evidence_requirements",
    }
