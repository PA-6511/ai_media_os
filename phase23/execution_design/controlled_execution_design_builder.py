from __future__ import annotations


def build_controlled_execution_design(phase22_result: dict) -> dict:
    if phase22_result.get("readiness_status") != "READY_FOR_PHASE23_PLANNING_ONLY":
        return {
            "status": "FAIL",
            "reason": "phase22_not_ready_for_phase23_planning_only",
        }

    if phase22_result.get("can_apply") is not False:
        return {
            "status": "FAIL",
            "reason": "phase22_can_apply_must_be_false",
        }

    planned_target_files = list(phase22_result.get("planned_target_files", []))[:1]

    return {
        "phase": "23",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "execution_scope": "single_file_controlled_design_only",
        "max_files_to_execute": 1,
        "execute_allowed": False,
        "auto_merge_allowed": False,
        "delete_allowed": False,
        "production_execute_allowed": False,
        "status": "CONTROLLED_EXECUTION_DESIGN_READY",
        "planned_target_files": planned_target_files,
        "next_step": "final_manual_gate_design",
    }
