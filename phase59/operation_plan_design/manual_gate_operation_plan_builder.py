from __future__ import annotations


def build_manual_gate_operation_plan(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE60_PLANNING_ONLY", "REJECT"],
        "operation_plan_gate_does_not_execute": True,
        "status": "MANUAL_GATE_OPERATION_PLAN_READY",
    }
