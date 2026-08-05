from __future__ import annotations


def evaluate_phase34_policy(
    final_review: dict,
    final_review_controls: dict,
    final_review_stop_conditions: dict,
    final_review_evidence_requirements: dict,
    manual_gate_final_pre_execution_review: dict,
) -> dict:
    reasons: list[str] = []

    if final_review.get("mode") != "DRY_RUN":
        reasons.append("mode_not_dry_run")
    if final_review.get("human_approval_required") is not True:
        reasons.append("human_approval_required_not_true")
    if final_review.get("max_files_to_execute") != 1:
        reasons.append("max_files_to_execute_not_1")
    if final_review.get("can_execute") is not False:
        reasons.append("can_execute_not_false")
    if final_review.get("execute_allowed") is not False:
        reasons.append("execute_allowed_not_false")
    if final_review.get("sandbox_scope_required") is not True:
        reasons.append("sandbox_scope_required_not_true")

    if final_review_controls.get("single_file_scope_required") is not True:
        reasons.append("single_file_scope_required_not_true")
    if final_review_controls.get("sandbox_scope_required") is not True:
        reasons.append("controls_sandbox_scope_required_not_true")
    if final_review_controls.get("final_review_controls_does_not_execute") is not True:
        reasons.append("final_review_controls_does_not_execute_not_true")

    if final_review_stop_conditions.get("stop_on_scope_violation") is not True:
        reasons.append("stop_on_scope_violation_not_true")
    if final_review_stop_conditions.get("stop_on_sandbox_violation") is not True:
        reasons.append("stop_on_sandbox_violation_not_true")
    if (
        final_review_stop_conditions.get("final_review_stop_conditions_does_not_execute")
        is not True
    ):
        reasons.append("final_review_stop_conditions_does_not_execute_not_true")

    if final_review_evidence_requirements.get("evidence_required") is not True:
        reasons.append("evidence_required_not_true")
    if final_review_evidence_requirements.get("missing_evidence_blocks_progress") is not True:
        reasons.append("missing_evidence_blocks_progress_not_true")
    if (
        final_review_evidence_requirements.get("final_review_evidence_does_not_execute")
        is not True
    ):
        reasons.append("final_review_evidence_does_not_execute_not_true")

    if manual_gate_final_pre_execution_review.get("approval_required") is not True:
        reasons.append("approval_required_not_true")
    if manual_gate_final_pre_execution_review.get("allow_does_not_execute") is not True:
        reasons.append("allow_does_not_execute_not_true")

    return {
        "policy_status": "PASS" if not reasons else "FAIL",
        "reasons": reasons,
    }
