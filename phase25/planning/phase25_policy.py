from __future__ import annotations


def evaluate_phase25_policy(plan: dict, evidence_format: dict, checklist: dict) -> dict:
    reasons: list[str] = []

    if plan.get("mode") != "DRY_RUN":
        reasons.append("mode_not_dry_run")
    if plan.get("human_approval_required") is not True:
        reasons.append("human_approval_required_not_true")
    if plan.get("max_files_to_execute") != 1:
        reasons.append("max_files_to_execute_not_1")

    targets = plan.get("planned_target_files", [])
    if not isinstance(targets, list) or len(targets) > 1:
        reasons.append("planned_target_files_out_of_scope")

    if plan.get("execute_allowed") is not False:
        reasons.append("execute_allowed_not_false")
    if plan.get("auto_merge_allowed") is not False:
        reasons.append("auto_merge_allowed_not_false")
    if plan.get("delete_allowed") is not False:
        reasons.append("delete_allowed_not_false")
    if plan.get("production_execute_allowed") is not False:
        reasons.append("production_execute_allowed_not_false")
    if plan.get("manual_approval_required") is not True:
        reasons.append("manual_approval_required_not_true")

    if evidence_format.get("evidence_required") is not True:
        reasons.append("evidence_required_not_true")
    if evidence_format.get("evidence_does_not_execute") is not True:
        reasons.append("evidence_does_not_execute_not_true")
    if checklist.get("status") != "EXECUTION_CHECKLIST_READY":
        reasons.append("execution_checklist_not_ready")

    return {
        "policy_status": "PASS" if not reasons else "FAIL",
        "reasons": reasons,
    }
