from __future__ import annotations


def build_go_live_review_controls(package: dict) -> dict:
    return {
        "controls_required": True,
        "dry_run_required": True,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "execute_allowed": False,
        "go_live_review_controls_does_not_execute": True,
        "status": "GO_LIVE_REVIEW_CONTROLS_READY",
    }
