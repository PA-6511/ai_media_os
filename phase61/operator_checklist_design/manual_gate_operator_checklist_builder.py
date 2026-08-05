from __future__ import annotations


def build_manual_gate_operator_checklist(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE62_PLANNING_ONLY", "REJECT"],
        "operator_checklist_gate_does_not_execute": True,
        "status": "MANUAL_GATE_OPERATOR_CHECKLIST_READY",
    }
