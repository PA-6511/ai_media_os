from __future__ import annotations


def build_design_review_package(phase19_result: dict) -> dict:
    if phase19_result.get("promotion_status") != "READY_FOR_PHASE20_DESIGN":
        return {
            "phase": "20",
            "mode": "DRY_RUN",
            "human_approval_required": True,
            "source_phase19_result": phase19_result,
            "review_checklist": [],
            "risk_summary": ["phase19_not_ready_for_phase20_design"],
            "status": "FAIL",
        }

    return {
        "phase": "20",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "source_phase19_result": phase19_result,
        "review_checklist": [
            "confirm_rc_scope_is_non_apply",
            "confirm_dry_run_constraints",
            "confirm_policy_gates_remain_blocking",
        ],
        "risk_summary": list(phase19_result.get("reasons", [])),
        "status": "REVIEW_READY",
    }
