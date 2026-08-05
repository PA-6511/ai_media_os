from __future__ import annotations


def build_manual_gate_release_planning(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE50_PLANNING_ONLY", "REJECT"],
        "release_planning_gate_does_not_execute": True,
        "status": "MANUAL_GATE_RELEASE_PLANNING_READY",
    }
