from __future__ import annotations


def build_manual_gate_final_preflight(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE57_PLANNING_ONLY", "REJECT"],
        "final_preflight_gate_does_not_execute": True,
        "status": "MANUAL_GATE_FINAL_PREFLIGHT_READY",
    }
