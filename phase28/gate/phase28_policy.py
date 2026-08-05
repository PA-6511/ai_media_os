from __future__ import annotations


def evaluate_phase28_policy(gate: dict, approval_schema: dict, evidence_spec: dict) -> dict:
    reasons: list[str] = []

    if gate.get("mode") != "DRY_RUN":
        reasons.append("mode_not_dry_run")
    if gate.get("human_approval_required") is not True:
        reasons.append("human_approval_required_not_true")
    if gate.get("max_files_to_execute") != 1:
        reasons.append("max_files_to_execute_not_1")
    if gate.get("execute_allowed") is not False:
        reasons.append("execute_allowed_not_false")
    if gate.get("gate_required") is not True:
        reasons.append("gate_required_not_true")

    if approval_schema.get("approval_required") is not True:
        reasons.append("approval_required_not_true")
    if approval_schema.get("allow_does_not_execute") is not True:
        reasons.append("allow_does_not_execute_not_true")

    if evidence_spec.get("evidence_required") is not True:
        reasons.append("evidence_required_not_true")
    if evidence_spec.get("evidence_does_not_execute") is not True:
        reasons.append("evidence_does_not_execute_not_true")

    return {
        "policy_status": "PASS" if not reasons else "FAIL",
        "reasons": reasons,
    }
