from __future__ import annotations


def build_manual_approval_gate(design: dict) -> dict:
    if design.get("status") != "LIMITED_DRY_RUN_DESIGN_READY":
        return {
            "status": "FAIL",
            "reason": "limited_dry_run_design_not_ready",
        }

    return {
        "gate_required": True,
        "approval_required": True,
        "allowed_decisions": [
            "ALLOW_PHASE31_PLANNING_ONLY",
            "REJECT",
            "NEEDS_REVISION",
        ],
        "allow_does_not_execute": True,
        "required_checks": [
            "single_file_scope",
            "sandbox_scope",
            "dry_run_mode",
            "no_delete",
            "no_production_path",
        ],
        "status": "MANUAL_APPROVAL_GATE_READY",
    }
