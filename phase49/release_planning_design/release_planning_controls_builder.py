from __future__ import annotations


def build_release_planning_controls(package: dict) -> dict:
    return {
        "controls_required": True,
        "dry_run_required": True,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "execute_allowed": False,
        "release_planning_controls_does_not_execute": True,
        "status": "RELEASE_PLANNING_CONTROLS_READY",
    }
