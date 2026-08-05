from __future__ import annotations


def build_operator_approval_stop_conditions(package: dict) -> dict:
    return {
        "stop_conditions_required": True,
        "stop_on_missing_manual_approval": True,
        "stop_on_missing_evidence": True,
        "stop_on_policy_violation": True,
        "stop_on_non_dry_run": True,
        "stop_on_multiple_files": True,
        "stop_on_sandbox_violation": True,
        "operator_approval_stop_conditions_does_not_execute": True,
        "status": "OPERATOR_APPROVAL_STOP_CONDITIONS_READY",
    }
