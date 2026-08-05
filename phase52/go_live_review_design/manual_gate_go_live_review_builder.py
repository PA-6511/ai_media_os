from __future__ import annotations


def build_manual_gate_go_live_review(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE53_PLANNING_ONLY", "REJECT"],
        "go_live_review_gate_does_not_execute": True,
        "status": "MANUAL_GATE_GO_LIVE_REVIEW_READY",
    }
