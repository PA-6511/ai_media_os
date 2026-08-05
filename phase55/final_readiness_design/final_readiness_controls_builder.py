from __future__ import annotations


def build_final_readiness_controls(package: dict) -> dict:
    return {
        "controls_required": True,
        "dry_run_required": True,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "execute_allowed": False,
        "final_readiness_controls_does_not_execute": True,
        "status": "FINAL_READINESS_CONTROLS_READY",
    }
