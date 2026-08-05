from __future__ import annotations


def evaluate_phase35_policy(
    readiness_package: dict,
    readiness_controls: dict,
    readiness_stop_conditions: dict,
    readiness_evidence_requirements: dict,
    manual_gate_readiness: dict,
) -> dict:
    reasons: list[str] = []

    if readiness_package.get("mode") != "DRY_RUN":
        reasons.append("mode_not_dry_run")
    if readiness_package.get("human_approval_required") is not True:
        reasons.append("human_approval_required_not_true")
    if readiness_package.get("max_files_to_execute") != 1:
        reasons.append("max_files_to_execute_not_1")
    if readiness_package.get("can_execute") is not False:
        reasons.append("can_execute_not_false")
    if readiness_package.get("execute_allowed") is not False:
        reasons.append("execute_allowed_not_false")
    if readiness_package.get("sandbox_scope_required") is not True:
        reasons.append("sandbox_scope_required_not_true")

    if readiness_controls.get("single_file_scope_required") is not True:
        reasons.append("single_file_scope_required_not_true")
    if readiness_controls.get("sandbox_scope_required") is not True:
        reasons.append("controls_sandbox_scope_required_not_true")
    if readiness_controls.get("readiness_controls_does_not_execute") is not True:
        reasons.append("readiness_controls_does_not_execute_not_true")

    if readiness_stop_conditions.get("stop_on_scope_violation") is not True:
        reasons.append("stop_on_scope_violation_not_true")
    if readiness_stop_conditions.get("stop_on_sandbox_violation") is not True:
        reasons.append("stop_on_sandbox_violation_not_true")
    if readiness_stop_conditions.get("readiness_stop_conditions_does_not_execute") is not True:
        reasons.append("readiness_stop_conditions_does_not_execute_not_true")

    if readiness_evidence_requirements.get("evidence_required") is not True:
        reasons.append("evidence_required_not_true")
    if readiness_evidence_requirements.get("missing_evidence_blocks_progress") is not True:
        reasons.append("missing_evidence_blocks_progress_not_true")
    if readiness_evidence_requirements.get("readiness_evidence_does_not_execute") is not True:
        reasons.append("readiness_evidence_does_not_execute_not_true")

    if manual_gate_readiness.get("approval_required") is not True:
        reasons.append("approval_required_not_true")
    if manual_gate_readiness.get("allow_does_not_execute") is not True:
        reasons.append("allow_does_not_execute_not_true")

    return {
        "policy_status": "PASS" if not reasons else "FAIL",
        "reasons": reasons,
    }
