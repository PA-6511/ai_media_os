from __future__ import annotations


def build_manual_gate_closure(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE45_PLANNING_ONLY", "REJECT"],
        "closure_gate_does_not_execute": True,
        "status": "MANUAL_GATE_CLOSURE_READY",
    }
