from __future__ import annotations


def build_readiness_controls(readiness_package: dict) -> dict:
    if readiness_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_READINESS_PACKAGE_READY":
        return {
            "status": "FAIL",
            "reason": "manual_dry_run_execution_readiness_package_not_ready",
        }

    return {
        "single_file_scope_required": True,
        "sandbox_scope_required": True,
        "manual_approval_record_required": True,
        "dry_run_mode_required": True,
        "readiness_controls_does_not_execute": True,
        "status": "READINESS_CONTROLS_READY",
    }
