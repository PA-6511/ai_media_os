from __future__ import annotations


def build_manual_gate_execution_plan(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE59_PLANNING_ONLY", "REJECT"],
        "execution_plan_gate_does_not_execute": True,
        "status": "MANUAL_GATE_EXECUTION_PLAN_READY",
    }
