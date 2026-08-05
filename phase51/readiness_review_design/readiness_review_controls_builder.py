from __future__ import annotations


def build_readiness_review_controls(package: dict) -> dict:
    return {
        "controls_required": True,
        "dry_run_required": True,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "execute_allowed": False,
        "readiness_review_controls_does_not_execute": True,
        "status": "READINESS_REVIEW_CONTROLS_READY",
    }
