from __future__ import annotations


def build_operator_checklist_controls(package: dict) -> dict:
    return {
        "controls_required": True,
        "dry_run_required": True,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "execute_allowed": False,
        "operator_checklist_controls_does_not_execute": True,
        "status": "OPERATOR_CHECKLIST_CONTROLS_READY",
    }
