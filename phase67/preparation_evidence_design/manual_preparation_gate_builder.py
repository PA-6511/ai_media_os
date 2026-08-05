from __future__ import annotations


def build_manual_preparation_gate(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE68_PLANNING_ONLY", "REJECT"],
        "manual_preparation_gate_does_not_execute": True,
        "status": "MANUAL_PREPARATION_GATE_READY",
    }
