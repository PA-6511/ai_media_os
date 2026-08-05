from __future__ import annotations


def build_final_check_controls(package: dict) -> dict:
    return {
        "controls_required": True,
        "dry_run_required": True,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "execute_allowed": False,
        "final_check_controls_does_not_execute": True,
        "status": "FINAL_CHECK_CONTROLS_READY",
    }
