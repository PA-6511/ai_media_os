from __future__ import annotations


def build_manual_gate_integration(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE48_PLANNING_ONLY", "REJECT"],
        "integration_gate_does_not_execute": True,
        "status": "MANUAL_GATE_INTEGRATION_READY",
    }
