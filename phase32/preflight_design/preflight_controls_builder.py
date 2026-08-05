from __future__ import annotations


def build_preflight_controls(preflight_package: dict) -> dict:
    if preflight_package.get("status") != "MANUAL_DRY_RUN_PREFLIGHT_PACKAGE_READY":
        return {
            "status": "FAIL",
            "reason": "manual_dry_run_preflight_package_not_ready",
        }

    return {
        "single_file_scope_required": True,
        "sandbox_scope_required": True,
        "approval_record_required": True,
        "dry_run_mode_required": True,
        "preflight_controls_does_not_execute": True,
        "status": "PREFLIGHT_CONTROLS_READY",
    }
