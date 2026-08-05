from __future__ import annotations


def build_manual_gate_cutover_planning(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE51_PLANNING_ONLY", "REJECT"],
        "cutover_planning_gate_does_not_execute": True,
        "status": "MANUAL_GATE_CUTOVER_PLANNING_READY",
    }
