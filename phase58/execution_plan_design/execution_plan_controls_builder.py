from __future__ import annotations


def build_execution_plan_controls(package: dict) -> dict:
    return {
        "controls_required": True,
        "dry_run_required": True,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "execute_allowed": False,
        "execution_plan_controls_does_not_execute": True,
        "status": "EXECUTION_PLAN_CONTROLS_READY",
    }
