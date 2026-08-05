from __future__ import annotations


def build_manual_gate_final_pre_execution_review(final_review: dict) -> dict:
    if final_review.get("status") != "FINAL_PRE_EXECUTION_REVIEW_READY":
        return {
            "status": "FAIL",
            "reason": "final_pre_execution_review_not_ready",
        }

    return {
        "gate_required": True,
        "approval_required": True,
        "allowed_decisions": [
            "ALLOW_PHASE35_PLANNING_ONLY",
            "REJECT",
            "NEEDS_REVISION",
        ],
        "allow_does_not_execute": True,
        "required_checks": [
            "single_file_scope",
            "sandbox_scope",
            "dry_run_mode",
            "final_review_controls_ready",
            "final_review_stop_conditions_ready",
            "final_review_evidence_requirements_ready",
        ],
        "status": "MANUAL_GATE_FINAL_PRE_EXECUTION_REVIEW_READY",
    }
