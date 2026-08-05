from __future__ import annotations


def evaluate_phase33_policy(
    approval_package: dict,
    final_approval_controls: dict,
    final_approval_stop_conditions: dict,
    final_approval_evidence_requirements: dict,
    manual_gate_final_approval: dict,
) -> dict:
    reasons: list[str] = []

    if approval_package.get("mode") != "DRY_RUN":
        reasons.append("mode_not_dry_run")
    if approval_package.get("human_approval_required") is not True:
        reasons.append("human_approval_required_not_true")
    if approval_package.get("max_files_to_execute") != 1:
        reasons.append("max_files_to_execute_not_1")
    if approval_package.get("can_execute") is not False:
        reasons.append("can_execute_not_false")
    if approval_package.get("execute_allowed") is not False:
        reasons.append("execute_allowed_not_false")
    if approval_package.get("sandbox_scope_required") is not True:
        reasons.append("sandbox_scope_required_not_true")

    if final_approval_controls.get("single_file_scope_required") is not True:
        reasons.append("single_file_scope_required_not_true")
    if final_approval_controls.get("sandbox_scope_required") is not True:
        reasons.append("controls_sandbox_scope_required_not_true")
    if final_approval_controls.get("final_approval_controls_does_not_execute") is not True:
        reasons.append("final_approval_controls_does_not_execute_not_true")

    if final_approval_stop_conditions.get("stop_on_scope_violation") is not True:
        reasons.append("stop_on_scope_violation_not_true")
    if final_approval_stop_conditions.get("stop_on_sandbox_violation") is not True:
        reasons.append("stop_on_sandbox_violation_not_true")
    if (
        final_approval_stop_conditions.get("final_approval_stop_conditions_does_not_execute")
        is not True
    ):
        reasons.append("final_approval_stop_conditions_does_not_execute_not_true")

    if final_approval_evidence_requirements.get("evidence_required") is not True:
        reasons.append("evidence_required_not_true")
    if (
        final_approval_evidence_requirements.get("missing_evidence_blocks_progress")
        is not True
    ):
        reasons.append("missing_evidence_blocks_progress_not_true")
    if (
        final_approval_evidence_requirements.get("final_approval_evidence_does_not_execute")
        is not True
    ):
        reasons.append("final_approval_evidence_does_not_execute_not_true")

    if manual_gate_final_approval.get("approval_required") is not True:
        reasons.append("approval_required_not_true")
    if manual_gate_final_approval.get("allow_does_not_execute") is not True:
        reasons.append("allow_does_not_execute_not_true")

    return {
        "policy_status": "PASS" if not reasons else "FAIL",
        "reasons": reasons,
    }
