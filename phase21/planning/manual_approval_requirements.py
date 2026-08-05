from __future__ import annotations


def build_manual_approval_requirements(plan: dict) -> dict:
    _ = plan
    return {
        "approval_required": True,
        "allowed_decisions": [
            "APPROVE_PHASE22_PLANNING_ONLY",
            "REJECT",
            "NEEDS_REVISION",
        ],
        "approve_effect": "allows_phase22_planning_only",
        "approve_does_not_apply": True,
        "required_checks": [
            "confirm_single_file_scope",
            "confirm_no_delete",
            "confirm_no_auto_merge",
            "confirm_no_production_apply",
            "confirm_dry_run_mode",
        ],
    }
