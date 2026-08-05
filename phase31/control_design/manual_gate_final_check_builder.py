from __future__ import annotations


def build_manual_gate_final_check(control_design: dict) -> dict:
    if control_design.get("status") != "PRE_EXECUTION_CONTROL_DESIGN_READY":
        return {
            "status": "FAIL",
            "reason": "pre_execution_control_design_not_ready",
        }

    return {
        "gate_required": True,
        "approval_required": True,
        "allowed_decisions": [
            "ALLOW_PHASE32_PLANNING_ONLY",
            "REJECT",
            "NEEDS_REVISION",
        ],
        "allow_does_not_execute": True,
        "required_checks": [
            "single_file_scope",
            "sandbox_scope",
            "dry_run_mode",
            "stop_conditions_ready",
            "evidence_requirements_ready",
        ],
        "status": "MANUAL_GATE_FINAL_CHECK_READY",
    }
