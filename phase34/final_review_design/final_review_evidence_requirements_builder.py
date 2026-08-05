from __future__ import annotations


def build_final_review_evidence_requirements(final_review: dict) -> dict:
    if final_review.get("status") != "FINAL_PRE_EXECUTION_REVIEW_READY":
        return {
            "status": "FAIL",
            "reason": "final_pre_execution_review_not_ready",
        }

    return {
        "evidence_required": True,
        "required_artifacts": [
            "target_file_path",
            "sandbox_proof",
            "manual_approval_record",
            "final_review_controls_snapshot",
            "final_review_stop_conditions_snapshot",
            "policy_evaluation_result",
        ],
        "missing_evidence_blocks_progress": True,
        "final_review_evidence_does_not_execute": True,
        "status": "FINAL_REVIEW_EVIDENCE_REQUIREMENTS_READY",
    }
