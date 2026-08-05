from __future__ import annotations


def build_manual_gate_staging(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE49_PLANNING_ONLY", "REJECT"],
        "staging_gate_does_not_execute": True,
        "status": "MANUAL_GATE_STAGING_READY",
    }
