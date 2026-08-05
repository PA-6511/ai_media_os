from __future__ import annotations


def build_sandbox_execution_constraints(design: dict) -> dict:
    if design.get("status") != "LIMITED_DRY_RUN_DESIGN_READY":
        return {
            "status": "FAIL",
            "reason": "limited_dry_run_design_not_ready",
        }

    return {
        "sandbox_only": True,
        "allowlist_within_sandbox": True,
        "delete_operation_forbidden": True,
        "production_path_forbidden": True,
        "constraints_does_not_execute": True,
        "status": "SANDBOX_EXECUTION_CONSTRAINTS_READY",
    }
