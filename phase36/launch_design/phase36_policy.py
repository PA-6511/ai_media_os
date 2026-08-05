"""Phase36 policy evaluator.

Validates all five launch-design sub-modules against safety constraints.
"""
from __future__ import annotations

from typing import Any


def evaluate_phase36_policy(
    launch_package: dict[str, Any],
    launch_controls: dict[str, Any],
    launch_stop_conditions: dict[str, Any],
    launch_evidence_requirements: dict[str, Any],
    manual_gate_launch: dict[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []

    # --- launch package ---
    if launch_package.get("mode") != "DRY_RUN":
        reasons.append("mode_not_DRY_RUN")
    if launch_package.get("human_approval_required") is not True:
        reasons.append("human_approval_required_not_true")
    if launch_package.get("max_files_to_execute") != 1:
        reasons.append("max_files_to_execute_not_1")
    if launch_package.get("can_execute") is not False:
        reasons.append("can_execute_not_false")
    if launch_package.get("execute_allowed") is not False:
        reasons.append("execute_allowed_not_false")
    if launch_package.get("sandbox_scope_required") is not True:
        reasons.append("sandbox_scope_required_not_true")

    # --- controls ---
    if launch_controls.get("single_file_scope_required") is not True:
        reasons.append("single_file_scope_required_not_true")
    if launch_controls.get("sandbox_scope_required") is not True:
        reasons.append("controls_sandbox_scope_required_not_true")
    if launch_controls.get("launch_controls_does_not_execute") is not True:
        reasons.append("launch_controls_does_not_execute_not_true")

    # --- stop conditions ---
    if launch_stop_conditions.get("stop_on_scope_violation") is not True:
        reasons.append("stop_on_scope_violation_not_true")
    if launch_stop_conditions.get("stop_on_sandbox_violation") is not True:
        reasons.append("stop_on_sandbox_violation_not_true")
    if launch_stop_conditions.get("launch_stop_conditions_does_not_execute") is not True:
        reasons.append("launch_stop_conditions_does_not_execute_not_true")

    # --- evidence ---
    if launch_evidence_requirements.get("evidence_required") is not True:
        reasons.append("evidence_required_not_true")
    if launch_evidence_requirements.get("missing_evidence_blocks_progress") is not True:
        reasons.append("missing_evidence_blocks_progress_not_true")
    if launch_evidence_requirements.get("launch_evidence_does_not_execute") is not True:
        reasons.append("launch_evidence_does_not_execute_not_true")

    # --- manual gate ---
    if manual_gate_launch.get("approval_required") is not True:
        reasons.append("approval_required_not_true")
    if manual_gate_launch.get("allow_does_not_execute") is not True:
        reasons.append("allow_does_not_execute_not_true")

    if reasons:
        return {"policy_status": "FAIL", "reasons": reasons}
    return {"policy_status": "PASS", "reasons": []}
