from __future__ import annotations


def evaluate_phase21_policy(plan: dict, approval_requirements: dict) -> dict:
    reasons: list[str] = []

    if plan.get("mode") != "DRY_RUN":
        reasons.append("mode_not_dry_run")
    if plan.get("max_files_to_apply") != 1:
        reasons.append("max_files_to_apply_not_1")

    targets = plan.get("planned_target_files", [])
    if not isinstance(targets, list) or len(targets) > 1:
        reasons.append("planned_target_files_out_of_scope")

    if plan.get("controlled_apply_allowed") is not False:
        reasons.append("controlled_apply_allowed_not_false")
    if plan.get("auto_merge_allowed") is not False:
        reasons.append("auto_merge_allowed_not_false")
    if plan.get("delete_allowed") is not False:
        reasons.append("delete_allowed_not_false")
    if plan.get("production_apply_allowed") is not False:
        reasons.append("production_apply_allowed_not_false")

    if approval_requirements.get("approval_required") is not True:
        reasons.append("approval_required_not_true")
    if approval_requirements.get("approve_does_not_apply") is not True:
        reasons.append("approve_does_not_apply_not_true")

    return {
        "policy_status": "PASS" if not reasons else "FAIL",
        "reasons": reasons,
    }
