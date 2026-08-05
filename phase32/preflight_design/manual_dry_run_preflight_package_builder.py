from __future__ import annotations


def build_manual_dry_run_preflight_package(phase31_result: dict) -> dict:
    if phase31_result.get("readiness_status") != "READY_FOR_PHASE32_PLANNING_ONLY":
        return {
            "status": "FAIL",
            "reason": "phase31_not_ready_for_phase32_planning_only",
        }

    if phase31_result.get("can_execute") is not False:
        return {
            "status": "FAIL",
            "reason": "phase31_can_execute_must_be_false",
        }

    return {
        "phase": "32",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "execution_scope": "manual_dry_run_execution_preflight_package_design_only",
        "max_files_to_execute": 1,
        "can_execute": False,
        "execute_allowed": False,
        "sandbox_scope_required": True,
        "status": "MANUAL_DRY_RUN_PREFLIGHT_PACKAGE_READY",
        "next_step": "define_preflight_controls_stop_and_evidence_requirements",
    }
