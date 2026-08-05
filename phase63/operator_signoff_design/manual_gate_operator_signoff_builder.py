from __future__ import annotations


def build_manual_gate_operator_signoff(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE64_PLANNING_ONLY", "REJECT"],
        "operator_signoff_gate_does_not_execute": True,
        "status": "MANUAL_GATE_OPERATOR_SIGNOFF_READY",
    }
