from __future__ import annotations


def evaluate_phase22_policy(
    approval_format: dict,
    checklist: dict,
    stop_conditions: dict,
) -> dict:
    reasons: list[str] = []

    if approval_format.get("mode") != "DRY_RUN":
        reasons.append("mode_not_dry_run")

    if approval_format.get("human_approval_required") is not True:
        reasons.append("human_approval_required_not_true")

    if approval_format.get("approval_required") is not True:
        reasons.append("approval_required_not_true")

    if approval_format.get("approve_does_not_apply") is not True:
        reasons.append("approve_does_not_apply_not_true")

    decisions = approval_format.get("decision_format", [])
    if "APPROVE_PHASE23_PLANNING_ONLY" not in decisions:
        reasons.append("decision_format_missing_planning_only_approve")

    if checklist.get("status") != "CHECKLIST_READY":
        reasons.append("checklist_not_ready")

    if stop_conditions.get("status") != "STOP_CONDITIONS_READY":
        reasons.append("stop_conditions_not_ready")

    return {
        "policy_status": "PASS" if not reasons else "FAIL",
        "reasons": reasons,
    }
