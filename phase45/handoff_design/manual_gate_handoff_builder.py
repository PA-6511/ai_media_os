from __future__ import annotations


def build_manual_gate_handoff(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE46_PLANNING_ONLY", "REJECT"],
        "handoff_gate_does_not_execute": True,
        "status": "MANUAL_GATE_HANDOFF_READY",
    }
