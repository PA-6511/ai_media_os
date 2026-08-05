from __future__ import annotations


def build_go_nogo_input(phase26_result: dict) -> dict:
    if phase26_result.get("readiness_status") != "READY_FOR_PHASE27_PLANNING_ONLY":
        return {
            "status": "FAIL",
            "reason": "phase26_not_ready_for_phase27_planning_only",
        }

    if phase26_result.get("can_execute") is not False:
        return {
            "status": "FAIL",
            "reason": "phase26_can_execute_must_be_false",
        }

    return {
        "phase": "27",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "decision_scope": "manual_dry_run_go_nogo_planning_only",
        "max_files_to_execute": 1,
        "execute_allowed": False,
        "status": "GO_NOGO_INPUT_READY",
        "required_inputs": [
            "manual_approval_reference",
            "policy_summary",
            "evidence_review_status",
            "abort_conditions_status",
        ],
        "next_step": "design_go_nogo_criteria",
    }
