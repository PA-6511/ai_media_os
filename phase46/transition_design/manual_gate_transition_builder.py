from __future__ import annotations


def build_manual_gate_transition(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE47_PLANNING_ONLY", "REJECT"],
        "transition_gate_does_not_execute": True,
        "status": "MANUAL_GATE_TRANSITION_READY",
    }
