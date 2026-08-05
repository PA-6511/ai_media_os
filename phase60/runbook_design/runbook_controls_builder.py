from __future__ import annotations


def build_runbook_controls(package: dict) -> dict:
    return {
        "controls_required": True,
        "dry_run_required": True,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "execute_allowed": False,
        "runbook_controls_does_not_execute": True,
        "status": "RUNBOOK_CONTROLS_READY",
    }
