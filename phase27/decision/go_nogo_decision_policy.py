from __future__ import annotations


def evaluate_go_nogo_decision_policy(go_nogo_input: dict, criteria: dict) -> dict:
    reasons: list[str] = []

    if go_nogo_input.get("mode") != "DRY_RUN":
        reasons.append("mode_not_dry_run")
    if go_nogo_input.get("human_approval_required") is not True:
        reasons.append("human_approval_required_not_true")
    if go_nogo_input.get("max_files_to_execute") != 1:
        reasons.append("max_files_to_execute_not_1")
    if go_nogo_input.get("execute_allowed") is not False:
        reasons.append("execute_allowed_not_false")

    if criteria.get("go_does_not_execute") is not True:
        reasons.append("go_does_not_execute_not_true")
    if criteria.get("status") != "GO_NOGO_CRITERIA_READY":
        reasons.append("criteria_not_ready")

    return {
        "policy_status": "PASS" if not reasons else "FAIL",
        "reasons": reasons,
    }
