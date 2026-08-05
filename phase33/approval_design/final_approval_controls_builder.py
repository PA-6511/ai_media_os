from __future__ import annotations


def build_final_approval_controls(approval_package: dict) -> dict:
    if (
        approval_package.get("status")
        != "MANUAL_DRY_RUN_EXECUTION_APPROVAL_PACKAGE_READY"
    ):
        return {
            "status": "FAIL",
            "reason": "manual_dry_run_execution_approval_package_not_ready",
        }

    return {
        "single_file_scope_required": True,
        "sandbox_scope_required": True,
        "manual_approval_record_required": True,
        "dry_run_mode_required": True,
        "final_approval_controls_does_not_execute": True,
        "status": "FINAL_APPROVAL_CONTROLS_READY",
    }
