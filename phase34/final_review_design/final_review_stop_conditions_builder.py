from __future__ import annotations


def build_final_review_stop_conditions(final_review: dict) -> dict:
    if final_review.get("status") != "FINAL_PRE_EXECUTION_REVIEW_READY":
        return {
            "status": "FAIL",
            "reason": "final_pre_execution_review_not_ready",
        }

    return {
        "stop_on_scope_violation": True,
        "stop_on_sandbox_violation": True,
        "stop_on_missing_manual_approval": True,
        "stop_on_missing_required_evidence": True,
        "stop_on_any_delete_operation": True,
        "stop_on_any_production_path": True,
        "final_review_stop_conditions_does_not_execute": True,
        "status": "FINAL_REVIEW_STOP_CONDITIONS_READY",
    }
