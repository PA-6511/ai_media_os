from __future__ import annotations


def design_go_nogo_decision(review: dict) -> dict:
    if review.get("status") != "PRE_EXECUTION_REVIEW_READY":
        return {
            "status": "FAIL",
            "reason": "review_not_ready",
        }

    return {
        "decision_options": [
            "GO_PHASE25_PLANNING_ONLY",
            "NO_GO",
            "NEEDS_REVISION",
        ],
        "go_means": "proceed_to_phase25_planning_only",
        "go_does_not_execute": True,
        "no_go_means": "stop_and_fix_findings",
        "status": "GO_NOGO_DECISION_READY",
    }
