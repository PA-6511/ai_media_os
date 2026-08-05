"""Phase40 policy evaluator."""
from __future__ import annotations

from typing import Any


def evaluate_phase40_policy(
    validation_package: dict[str, Any],
    validation_controls: dict[str, Any],
    validation_stop_conditions: dict[str, Any],
    validation_evidence_requirements: dict[str, Any],
    manual_gate_validation: dict[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []

    # --- validation package ---
    if validation_package.get("mode") != "DRY_RUN":
        reasons.append("mode_not_DRY_RUN")
    if validation_package.get("human_approval_required") is not True:
        reasons.append("human_approval_required_not_true")
    if validation_package.get("max_files_to_execute") != 1:
        reasons.append("max_files_to_execute_not_1")
    if validation_package.get("can_execute") is not False:
        reasons.append("can_execute_not_false")
    if validation_package.get("execute_allowed") is not False:
        reasons.append("execute_allowed_not_false")
    if validation_package.get("sandbox_scope_required") is not True:
        reasons.append("sandbox_scope_required_not_true")

    # --- controls ---
    if validation_controls.get("single_file_scope_required") is not True:
        reasons.append("single_file_scope_required_not_true")
    if validation_controls.get("sandbox_scope_required") is not True:
        reasons.append("controls_sandbox_scope_required_not_true")
    if validation_controls.get("validation_controls_does_not_execute") is not True:
        reasons.append("validation_controls_does_not_execute_not_true")

    # --- stop conditions ---
    if validation_stop_conditions.get("stop_on_scope_violation") is not True:
        reasons.append("stop_on_scope_violation_not_true")
    if validation_stop_conditions.get("stop_on_sandbox_violation") is not True:
        reasons.append("stop_on_sandbox_violation_not_true")
    if validation_stop_conditions.get("validation_stop_conditions_does_not_execute") is not True:
        reasons.append("validation_stop_conditions_does_not_execute_not_true")

    # --- evidence ---
    if validation_evidence_requirements.get("evidence_required") is not True:
        reasons.append("evidence_required_not_true")
    if validation_evidence_requirements.get("missing_evidence_blocks_progress") is not True:
        reasons.append("missing_evidence_blocks_progress_not_true")
    if validation_evidence_requirements.get("validation_evidence_does_not_execute") is not True:
        reasons.append("validation_evidence_does_not_execute_not_true")

    # --- manual gate ---
    if manual_gate_validation.get("approval_required") is not True:
        reasons.append("approval_required_not_true")
    if manual_gate_validation.get("allow_does_not_execute") is not True:
        reasons.append("allow_does_not_execute_not_true")

    if reasons:
        return {"policy_status": "FAIL", "reasons": reasons}
    return {"policy_status": "PASS", "reasons": []}
