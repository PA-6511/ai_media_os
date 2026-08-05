from __future__ import annotations


def evaluate_phase23_policy(design: dict, gate: dict, stop_verify: dict) -> dict:
    reasons: list[str] = []

    if design.get("mode") != "DRY_RUN":
        reasons.append("mode_not_dry_run")
    if design.get("human_approval_required") is not True:
        reasons.append("human_approval_required_not_true")
    if design.get("max_files_to_execute") != 1:
        reasons.append("max_files_to_execute_not_1")

    targets = design.get("planned_target_files", [])
    if not isinstance(targets, list) or len(targets) > 1:
        reasons.append("planned_target_files_out_of_scope")

    if design.get("execute_allowed") is not False:
        reasons.append("execute_allowed_not_false")
    if design.get("auto_merge_allowed") is not False:
        reasons.append("auto_merge_allowed_not_false")
    if design.get("delete_allowed") is not False:
        reasons.append("delete_allowed_not_false")
    if design.get("production_execute_allowed") is not False:
        reasons.append("production_execute_allowed_not_false")

    if gate.get("approval_required") is not True:
        reasons.append("gate_approval_required_not_true")
    if gate.get("approve_does_not_execute") is not True:
        reasons.append("approve_does_not_execute_not_true")

    if stop_verify.get("status") != "PASS":
        reasons.append("stop_condition_verify_not_pass")

    return {
        "policy_status": "PASS" if not reasons else "FAIL",
        "reasons": reasons,
    }
