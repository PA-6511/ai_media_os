from __future__ import annotations


def build_manual_gate_operator_finalize(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE65_PLANNING_ONLY", "REJECT"],
        "operator_finalize_gate_does_not_execute": True,
        "status": "MANUAL_GATE_OPERATOR_FINALIZE_READY",
    }
