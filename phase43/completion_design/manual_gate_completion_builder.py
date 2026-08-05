from __future__ import annotations


def build_manual_gate_completion(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE44_PLANNING_ONLY", "REJECT"],
        "allow_does_not_execute": True,
        "status": "MANUAL_GATE_COMPLETION_READY",
    }
