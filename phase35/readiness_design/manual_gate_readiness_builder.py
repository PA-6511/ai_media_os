from __future__ import annotations


def build_manual_gate_readiness(readiness_package: dict) -> dict:
    if readiness_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_READINESS_PACKAGE_READY":
        return {
            "status": "FAIL",
            "reason": "manual_dry_run_execution_readiness_package_not_ready",
        }

    return {
        "gate_required": True,
        "approval_required": True,
        "allowed_decisions": [
            "ALLOW_PHASE36_PLANNING_ONLY",
            "REJECT",
            "NEEDS_REVISION",
        ],
        "allow_does_not_execute": True,
        "required_checks": [
            "single_file_scope",
            "sandbox_scope",
            "dry_run_mode",
            "readiness_controls_ready",
            "readiness_stop_conditions_ready",
            "readiness_evidence_requirements_ready",
        ],
        "status": "MANUAL_GATE_READINESS_READY",
    }
