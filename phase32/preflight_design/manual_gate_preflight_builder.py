from __future__ import annotations


def build_manual_gate_preflight(preflight_package: dict) -> dict:
    if preflight_package.get("status") != "MANUAL_DRY_RUN_PREFLIGHT_PACKAGE_READY":
        return {
            "status": "FAIL",
            "reason": "manual_dry_run_preflight_package_not_ready",
        }

    return {
        "gate_required": True,
        "approval_required": True,
        "allowed_decisions": [
            "ALLOW_PHASE33_PLANNING_ONLY",
            "REJECT",
            "NEEDS_REVISION",
        ],
        "allow_does_not_execute": True,
        "required_checks": [
            "single_file_scope",
            "sandbox_scope",
            "dry_run_mode",
            "preflight_controls_ready",
            "preflight_stop_conditions_ready",
            "preflight_evidence_requirements_ready",
        ],
        "status": "MANUAL_GATE_PREFLIGHT_READY",
    }
