from __future__ import annotations


def build_final_manual_gate(design: dict) -> dict:
    _ = design
    return {
        "gate_required": True,
        "approval_required": True,
        "allowed_decisions": [
            "APPROVE_PHASE24_PLANNING_ONLY",
            "REJECT",
            "NEEDS_REVISION",
        ],
        "approve_does_not_execute": True,
        "required_evidence": [
            "single_file_scope_confirmed",
            "stop_conditions_verified",
            "dry_run_mode_confirmed",
            "no_delete_confirmed",
            "no_production_execute_confirmed",
        ],
        "status": "FINAL_MANUAL_GATE_READY",
    }
