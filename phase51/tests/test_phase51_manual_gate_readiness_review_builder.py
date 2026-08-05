from phase51.readiness_review_design.manual_gate_readiness_review_builder import (
    build_manual_gate_readiness_review,
)


def test_manual_gate_readiness_review_allows_phase52_planning_only() -> None:
    gate = build_manual_gate_readiness_review({"status": "READINESS_REVIEW_PACKAGE_READY"})
    assert gate["status"] == "MANUAL_GATE_READINESS_REVIEW_READY"
    assert gate["readiness_review_gate_does_not_execute"] is True
    assert "ALLOW_PHASE52_PLANNING_ONLY" in gate["allowed_decisions"]
