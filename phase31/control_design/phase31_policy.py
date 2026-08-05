from __future__ import annotations


def evaluate_phase31_policy(
    control_design: dict,
    stop_conditions: dict,
    evidence_requirements: dict,
    manual_gate_final_check: dict,
) -> dict:
    reasons: list[str] = []

    if control_design.get("mode") != "DRY_RUN":
        reasons.append("mode_not_dry_run")
    if control_design.get("human_approval_required") is not True:
        reasons.append("human_approval_required_not_true")
    if control_design.get("execute_allowed") is not False:
        reasons.append("execute_allowed_not_false")
    if control_design.get("can_execute") is not False:
        reasons.append("can_execute_not_false")
    if control_design.get("max_files_to_execute") != 1:
        reasons.append("max_files_to_execute_not_1")
    if control_design.get("sandbox_scope_required") is not True:
        reasons.append("sandbox_scope_required_not_true")

    if stop_conditions.get("stop_on_scope_violation") is not True:
        reasons.append("stop_on_scope_violation_not_true")
    if stop_conditions.get("stop_on_sandbox_violation") is not True:
        reasons.append("stop_on_sandbox_violation_not_true")
    if stop_conditions.get("stop_conditions_does_not_execute") is not True:
        reasons.append("stop_conditions_does_not_execute_not_true")

    if evidence_requirements.get("evidence_required") is not True:
        reasons.append("evidence_required_not_true")
    if evidence_requirements.get("missing_evidence_blocks_progress") is not True:
        reasons.append("missing_evidence_blocks_progress_not_true")
    if evidence_requirements.get("evidence_does_not_execute") is not True:
        reasons.append("evidence_does_not_execute_not_true")

    if manual_gate_final_check.get("approval_required") is not True:
        reasons.append("approval_required_not_true")
    if manual_gate_final_check.get("allow_does_not_execute") is not True:
        reasons.append("allow_does_not_execute_not_true")

    return {
        "policy_status": "PASS" if not reasons else "FAIL",
        "reasons": reasons,
    }
