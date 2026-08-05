from __future__ import annotations


def build_preflight_stop_conditions(preflight_package: dict) -> dict:
    if preflight_package.get("status") != "MANUAL_DRY_RUN_PREFLIGHT_PACKAGE_READY":
        return {
            "status": "FAIL",
            "reason": "manual_dry_run_preflight_package_not_ready",
        }

    return {
        "stop_on_scope_violation": True,
        "stop_on_sandbox_violation": True,
        "stop_on_missing_manual_approval": True,
        "stop_on_missing_required_evidence": True,
        "stop_on_any_delete_operation": True,
        "stop_on_any_production_path": True,
        "preflight_stop_conditions_does_not_execute": True,
        "status": "PREFLIGHT_STOP_CONDITIONS_READY",
    }
