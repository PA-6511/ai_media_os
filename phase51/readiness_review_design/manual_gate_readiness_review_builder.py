from __future__ import annotations


def build_manual_gate_readiness_review(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE52_PLANNING_ONLY", "REJECT"],
        "readiness_review_gate_does_not_execute": True,
        "status": "MANUAL_GATE_READINESS_REVIEW_READY",
    }
