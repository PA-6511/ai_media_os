from __future__ import annotations


def build_manual_gate_final_approval(approval_package: dict) -> dict:
    if (
        approval_package.get("status")
        != "MANUAL_DRY_RUN_EXECUTION_APPROVAL_PACKAGE_READY"
    ):
        return {
            "status": "FAIL",
            "reason": "manual_dry_run_execution_approval_package_not_ready",
        }

    return {
        "gate_required": True,
        "approval_required": True,
        "allowed_decisions": [
            "ALLOW_PHASE34_PLANNING_ONLY",
            "REJECT",
            "NEEDS_REVISION",
        ],
        "allow_does_not_execute": True,
        "required_checks": [
            "single_file_scope",
            "sandbox_scope",
            "dry_run_mode",
            "final_approval_controls_ready",
            "final_approval_stop_conditions_ready",
            "final_approval_evidence_requirements_ready",
        ],
        "status": "MANUAL_GATE_FINAL_APPROVAL_READY",
    }
