from __future__ import annotations


def build_manual_gate_runbook(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE61_PLANNING_ONLY", "REJECT"],
        "runbook_gate_does_not_execute": True,
        "status": "MANUAL_GATE_RUNBOOK_READY",
    }
