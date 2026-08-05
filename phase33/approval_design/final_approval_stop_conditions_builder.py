from __future__ import annotations


def build_final_approval_stop_conditions(approval_package: dict) -> dict:
    if (
        approval_package.get("status")
        != "MANUAL_DRY_RUN_EXECUTION_APPROVAL_PACKAGE_READY"
    ):
        return {
            "status": "FAIL",
            "reason": "manual_dry_run_execution_approval_package_not_ready",
        }

    return {
        "stop_on_scope_violation": True,
        "stop_on_sandbox_violation": True,
        "stop_on_missing_manual_approval": True,
        "stop_on_missing_required_evidence": True,
        "stop_on_any_delete_operation": True,
        "stop_on_any_production_path": True,
        "final_approval_stop_conditions_does_not_execute": True,
        "status": "FINAL_APPROVAL_STOP_CONDITIONS_READY",
    }
