from phase52.go_live_review_design.manual_gate_go_live_review_builder import (
    build_manual_gate_go_live_review,
)


def test_manual_gate_go_live_review_allows_phase53_planning_only() -> None:
    gate = build_manual_gate_go_live_review({"status": "GO_LIVE_REVIEW_PACKAGE_READY"})
    assert gate["status"] == "MANUAL_GATE_GO_LIVE_REVIEW_READY"
    assert gate["go_live_review_gate_does_not_execute"] is True
    assert "ALLOW_PHASE53_PLANNING_ONLY" in gate["allowed_decisions"]
