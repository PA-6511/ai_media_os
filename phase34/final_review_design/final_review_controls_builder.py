from __future__ import annotations


def build_final_review_controls(final_review: dict) -> dict:
    if final_review.get("status") != "FINAL_PRE_EXECUTION_REVIEW_READY":
        return {
            "status": "FAIL",
            "reason": "final_pre_execution_review_not_ready",
        }

    return {
        "single_file_scope_required": True,
        "sandbox_scope_required": True,
        "manual_approval_record_required": True,
        "dry_run_mode_required": True,
        "final_review_controls_does_not_execute": True,
        "status": "FINAL_REVIEW_CONTROLS_READY",
    }
