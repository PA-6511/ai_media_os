from __future__ import annotations


def build_manual_gate_final_go_review(package: dict) -> dict:
    return {
        "gate_required": True,
        "allowed_decisions": ["ALLOW_PHASE54_PLANNING_ONLY", "REJECT"],
        "final_go_review_gate_does_not_execute": True,
        "status": "MANUAL_GATE_FINAL_GO_REVIEW_READY",
    }
