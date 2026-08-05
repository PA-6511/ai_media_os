from __future__ import annotations


def evaluate_phase29_policy(gate_input: dict, checklist: dict, evidence_gate: dict) -> dict:
    reasons: list[str] = []

    if gate_input.get("mode") != "DRY_RUN":
        reasons.append("mode_not_dry_run")
    if gate_input.get("human_approval_required") is not True:
        reasons.append("human_approval_required_not_true")
    if gate_input.get("max_files_to_execute") != 1:
        reasons.append("max_files_to_execute_not_1")
    if gate_input.get("execute_allowed") is not False:
        reasons.append("execute_allowed_not_false")

    if checklist.get("checklist_required") is not True:
        reasons.append("checklist_required_not_true")
    if checklist.get("checklist_does_not_execute") is not True:
        reasons.append("checklist_does_not_execute_not_true")

    if evidence_gate.get("evidence_gate_required") is not True:
        reasons.append("evidence_gate_required_not_true")
    if evidence_gate.get("evidence_does_not_execute") is not True:
        reasons.append("evidence_does_not_execute_not_true")

    return {
        "policy_status": "PASS" if not reasons else "FAIL",
        "reasons": reasons,
    }
