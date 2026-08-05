from __future__ import annotations

_REQUIRED_KEYS = [
    "phase",
    "mode",
    "human_approval_required",
    "apply_scope",
    "max_files_to_apply",
    "controlled_apply_allowed",
    "auto_merge_allowed",
    "delete_allowed",
    "production_apply_allowed",
    "manual_approval_required_for_next",
    "planned_target_files",
    "status",
]


def validate_controlled_apply_plan(plan: dict) -> dict:
    findings: list[str] = []

    missing = [key for key in _REQUIRED_KEYS if key not in plan]
    if missing:
        findings.append("missing_keys:" + ",".join(missing))

    if plan.get("phase") != "21":
        findings.append("phase_must_be_21")
    if plan.get("mode") != "DRY_RUN":
        findings.append("mode_must_be_dry_run")
    if plan.get("human_approval_required") is not True:
        findings.append("human_approval_required_must_be_true")
    if plan.get("apply_scope") != "single_file_planning_only":
        findings.append("apply_scope_invalid")
    if plan.get("max_files_to_apply") != 1:
        findings.append("max_files_to_apply_must_be_1")
    if plan.get("controlled_apply_allowed") is not False:
        findings.append("controlled_apply_allowed_must_be_false")
    if plan.get("auto_merge_allowed") is not False:
        findings.append("auto_merge_allowed_must_be_false")
    if plan.get("delete_allowed") is not False:
        findings.append("delete_allowed_must_be_false")
    if plan.get("production_apply_allowed") is not False:
        findings.append("production_apply_allowed_must_be_false")
    if plan.get("manual_approval_required_for_next") is not True:
        findings.append("manual_approval_required_for_next_must_be_true")

    targets = plan.get("planned_target_files", [])
    if not isinstance(targets, list):
        findings.append("planned_target_files_must_be_list")
    elif len(targets) > 1:
        findings.append("planned_target_files_exceeds_single_file_limit")

    status = "PASS" if not findings else "FAIL"
    return {"status": status, "findings": findings}
