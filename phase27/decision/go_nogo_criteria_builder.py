from __future__ import annotations


def build_go_nogo_criteria(go_nogo_input: dict) -> dict:
    if go_nogo_input.get("status") != "GO_NOGO_INPUT_READY":
        return {
            "status": "FAIL",
            "reason": "go_nogo_input_not_ready",
        }

    return {
        "criteria": [
            "single_file_scope_confirmed",
            "dry_run_mode_confirmed",
            "manual_approval_present",
            "abort_conditions_defined",
            "evidence_review_ready",
            "policy_result_pass",
        ],
        "go_option": "GO_PHASE28_PLANNING_ONLY",
        "no_go_option": "NO_GO",
        "needs_revision_option": "NEEDS_REVISION",
        "go_does_not_execute": True,
        "status": "GO_NOGO_CRITERIA_READY",
    }
