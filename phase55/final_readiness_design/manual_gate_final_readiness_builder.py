from __future__ import annotations


def build_manual_gate_final_readiness(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE56_PLANNING_ONLY", "REJECT"],
        "final_readiness_gate_does_not_execute": True,
        "status": "MANUAL_GATE_FINAL_READINESS_READY",
    }
