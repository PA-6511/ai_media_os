from __future__ import annotations


def build_stop_conditions(control_design: dict) -> dict:
    if control_design.get("status") != "PRE_EXECUTION_CONTROL_DESIGN_READY":
        return {
            "status": "FAIL",
            "reason": "pre_execution_control_design_not_ready",
        }

    return {
        "stop_on_scope_violation": True,
        "stop_on_sandbox_violation": True,
        "stop_on_missing_manual_approval": True,
        "stop_on_non_dry_run_request": True,
        "stop_on_any_delete_operation": True,
        "stop_on_any_production_path": True,
        "stop_conditions_does_not_execute": True,
        "status": "STOP_CONDITIONS_READY",
    }
