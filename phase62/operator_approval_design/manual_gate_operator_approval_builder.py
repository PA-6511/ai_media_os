from __future__ import annotations


def build_manual_gate_operator_approval(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE63_PLANNING_ONLY", "REJECT"],
        "operator_approval_gate_does_not_execute": True,
        "status": "MANUAL_GATE_OPERATOR_APPROVAL_READY",
    }
