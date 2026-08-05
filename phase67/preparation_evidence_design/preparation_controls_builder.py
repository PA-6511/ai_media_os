from __future__ import annotations


def build_preparation_controls(package: dict) -> dict:
    return {
        "controls_required": True,
        "dry_run_required": True,
        "human_approval_required": True,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "execute_allowed": False,
        "preparation_controls_does_not_execute": True,
        "status": "PREPARATION_CONTROLS_READY",
    }
