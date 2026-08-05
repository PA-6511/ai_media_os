from __future__ import annotations


def build_dry_run_execution_plan(phase24_result: dict) -> dict:
    if phase24_result.get("readiness_status") != "READY_FOR_PHASE25_PLANNING_ONLY":
        return {
            "status": "FAIL",
            "reason": "phase24_not_ready_for_phase25_planning_only",
        }

    if phase24_result.get("can_execute") is not False:
        return {
            "status": "FAIL",
            "reason": "phase24_can_execute_must_be_false",
        }

    planned_target_files = list(phase24_result.get("planned_target_files", []))[:1]

    return {
        "phase": "25",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "execution_plan_scope": "single_file_dry_run_planning_only",
        "max_files_to_execute": 1,
        "execute_allowed": False,
        "auto_merge_allowed": False,
        "delete_allowed": False,
        "production_execute_allowed": False,
        "manual_approval_required": True,
        "planned_target_files": planned_target_files,
        "status": "DRY_RUN_EXECUTION_PLAN_READY",
        "next_step": "design_evidence_and_review_materials",
    }
