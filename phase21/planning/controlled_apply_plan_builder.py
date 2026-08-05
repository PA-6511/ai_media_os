from __future__ import annotations


def build_controlled_apply_plan(phase20_result: dict) -> dict:
    if phase20_result.get("readiness_status") != "READY_FOR_PHASE21_PLANNING":
        return {
            "status": "FAIL",
            "reason": "phase20_not_ready_for_phase21_planning",
        }

    if phase20_result.get("can_apply") is not False:
        return {
            "status": "FAIL",
            "reason": "phase20_can_apply_must_be_false",
        }

    planned_target_files = list(phase20_result.get("planned_target_files", []))[:1]

    return {
        "phase": "21",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "source_phase20_result": phase20_result,
        "apply_scope": "single_file_planning_only",
        "max_files_to_apply": 1,
        "controlled_apply_allowed": False,
        "auto_merge_allowed": False,
        "delete_allowed": False,
        "production_apply_allowed": False,
        "status": "CONTROLLED_APPLY_PLAN_DRAFT",
        "planned_target_files": planned_target_files,
        "manual_approval_required_for_next": True,
        "next_step": "manual_review_before_phase22",
    }
