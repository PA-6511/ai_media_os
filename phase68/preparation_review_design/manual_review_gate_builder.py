from __future__ import annotations


def build_manual_review_gate(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE69_PLANNING_ONLY", "REJECT"],
        "manual_review_gate_does_not_execute": True,
        "status": "MANUAL_REVIEW_GATE_READY",
    }
