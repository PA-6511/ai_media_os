from __future__ import annotations


def evaluate_phase24_policy(review: dict, decision_design: dict) -> dict:
    reasons: list[str] = []

    if review.get("mode") != "DRY_RUN":
        reasons.append("mode_not_dry_run")
    if review.get("human_approval_required") is not True:
        reasons.append("human_approval_required_not_true")
    if review.get("max_files_to_execute") != 1:
        reasons.append("max_files_to_execute_not_1")
    if review.get("execute_allowed") is not False:
        reasons.append("execute_allowed_not_false")

    options = decision_design.get("decision_options", [])
    if "GO_PHASE25_PLANNING_ONLY" not in options:
        reasons.append("go_planning_option_missing")
    if decision_design.get("go_does_not_execute") is not True:
        reasons.append("go_does_not_execute_not_true")

    return {
        "policy_status": "PASS" if not reasons else "FAIL",
        "reasons": reasons,
    }
