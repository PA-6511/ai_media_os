from __future__ import annotations


def build_limited_dry_run_preparation_review_package(phase67_report: dict) -> dict:
    if phase67_report.get("readiness_status") != "READY_FOR_PHASE68_PLANNING_ONLY":
        return {"status": "FAIL", "reason": "phase67_readiness_status_not_met"}
    if phase67_report.get("can_execute") is not False:
        return {"status": "FAIL", "reason": "phase67_can_execute_must_be_false"}
    if phase67_report.get("execute_allowed") is not False:
        return {"status": "FAIL", "reason": "phase67_execute_allowed_must_be_false"}

    return {
        "phase": 68,
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "package_scope": "limited_dry_run_preparation_review_package_design_only",
        "can_execute": False,
        "execute_allowed": False,
        "max_files_to_execute": 1,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "status": "PREPARATION_REVIEW_PACKAGE_READY",
        "next_step": "build_review_controls",
    }
