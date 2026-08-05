from __future__ import annotations

_REQUIRED_STOP_CONDITIONS = {
    "target_files_count_exceeds_1",
    "manual_approval_missing",
    "policy_violation_detected",
    "dry_run_disabled",
    "any_delete_instruction_detected",
    "any_production_instruction_detected",
}


def verify_stop_conditions(stop_conditions: dict) -> dict:
    conditions = stop_conditions.get("conditions")
    if not isinstance(conditions, list):
        return {
            "status": "FAIL",
            "findings": ["conditions_not_list"],
        }

    missing = sorted(list(_REQUIRED_STOP_CONDITIONS - set(conditions)))
    if missing:
        return {
            "status": "FAIL",
            "findings": ["missing_conditions:" + ",".join(missing)],
        }

    return {
        "status": "PASS",
        "findings": [],
    }
