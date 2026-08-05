from __future__ import annotations


def evaluate_phase30_policy(design: dict, constraints: dict, approval_gate: dict) -> dict:
    reasons: list[str] = []

    if design.get("mode") != "DRY_RUN":
        reasons.append("mode_not_dry_run")
    if design.get("human_approval_required") is not True:
        reasons.append("human_approval_required_not_true")
    if design.get("max_files_to_execute") != 1:
        reasons.append("max_files_to_execute_not_1")
    if design.get("execute_allowed") is not False:
        reasons.append("execute_allowed_not_false")
    if design.get("sandbox_scope_required") is not True:
        reasons.append("sandbox_scope_required_not_true")

    if constraints.get("sandbox_only") is not True:
        reasons.append("sandbox_only_not_true")
    if constraints.get("allowlist_within_sandbox") is not True:
        reasons.append("allowlist_within_sandbox_not_true")
    if constraints.get("constraints_does_not_execute") is not True:
        reasons.append("constraints_does_not_execute_not_true")

    if approval_gate.get("approval_required") is not True:
        reasons.append("approval_required_not_true")
    if approval_gate.get("allow_does_not_execute") is not True:
        reasons.append("allow_does_not_execute_not_true")

    return {
        "policy_status": "PASS" if not reasons else "FAIL",
        "reasons": reasons,
    }
