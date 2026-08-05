from __future__ import annotations


def build_transition_controls(package: dict) -> dict:
    return {
        "controls_required": True,
        "dry_run_required": True,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "execute_allowed": False,
        "transition_controls_does_not_execute": True,
        "status": "TRANSITION_CONTROLS_READY",
    }
