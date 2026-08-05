from __future__ import annotations


def evaluate_phase67_policy(
    package: dict,
    controls: dict,
    evidence_requirements: dict,
    manual_preparation_gate: dict,
) -> dict:
    reasons: list[str] = []

    if package.get("mode") != "DRY_RUN":
        reasons.append("package.mode must be DRY_RUN")
    if package.get("human_approval_required") is not True:
        reasons.append("package.human_approval_required must be True")
    if package.get("can_execute") is not False:
        reasons.append("package.can_execute must be False")
    if package.get("execute_allowed") is not False:
        reasons.append("package.execute_allowed must be False")
    if package.get("max_files_to_execute") != 1:
        reasons.append("package.max_files_to_execute must be 1")
    if package.get("sandbox_scope_required") is not True:
        reasons.append("package.sandbox_scope_required must be True")
    if package.get("single_file_scope_required") is not True:
        reasons.append("package.single_file_scope_required must be True")

    if controls.get("preparation_controls_does_not_execute") is not True:
        reasons.append("controls.preparation_controls_does_not_execute must be True")
    if evidence_requirements.get("evidence_required") is not True:
        reasons.append("evidence_requirements.evidence_required must be True")
    if evidence_requirements.get("missing_evidence_blocks_progress") is not True:
        reasons.append("evidence_requirements.missing_evidence_blocks_progress must be True")
    if evidence_requirements.get("preparation_evidence_does_not_execute") is not True:
        reasons.append("evidence_requirements.preparation_evidence_does_not_execute must be True")
    if manual_preparation_gate.get("gate_required") is not True:
        reasons.append("manual_preparation_gate.gate_required must be True")
    if manual_preparation_gate.get("manual_preparation_gate_does_not_execute") is not True:
        reasons.append(
            "manual_preparation_gate.manual_preparation_gate_does_not_execute must be True"
        )

    if reasons:
        return {"policy_status": "FAIL", "reasons": reasons}
    return {"policy_status": "PASS", "reasons": []}
