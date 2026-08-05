from __future__ import annotations


def build_review_controls(package: dict) -> dict:
    return {
        "controls_required": True,
        "dry_run_required": True,
        "human_approval_required": True,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "execute_allowed": False,
        "review_controls_does_not_execute": True,
        "status": "REVIEW_CONTROLS_READY",
    }
