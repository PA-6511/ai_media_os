from __future__ import annotations


def build_manual_gate_final_check(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE58_PLANNING_ONLY", "REJECT"],
        "final_check_gate_does_not_execute": True,
        "status": "MANUAL_GATE_FINAL_CHECK_READY",
    }
