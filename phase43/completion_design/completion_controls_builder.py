from __future__ import annotations


def build_completion_controls(package: dict) -> dict:
    return {
        "controls_required": True,
        "dry_run_required": True,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "execute_allowed": False,
        "controls_do_not_execute": True,
        "status": "COMPLETION_CONTROLS_READY",
    }
