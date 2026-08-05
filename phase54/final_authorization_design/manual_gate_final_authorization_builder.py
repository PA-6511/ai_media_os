from __future__ import annotations


def build_manual_gate_final_authorization(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE55_PLANNING_ONLY", "REJECT"],
        "final_authorization_gate_does_not_execute": True,
        "status": "MANUAL_GATE_FINAL_AUTHORIZATION_READY",
    }
