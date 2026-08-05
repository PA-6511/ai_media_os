from phase53.final_go_review_design.manual_gate_final_go_review_builder import (
    build_manual_gate_final_go_review,
)


def test_manual_gate_final_go_review_allows_phase54_planning_only() -> None:
    gate = build_manual_gate_final_go_review({"status": "FINAL_GO_REVIEW_PACKAGE_READY"})
    assert gate["status"] == "MANUAL_GATE_FINAL_GO_REVIEW_READY"
    assert gate["final_go_review_gate_does_not_execute"] is True
    assert "ALLOW_PHASE54_PLANNING_ONLY" in gate["allowed_decisions"]
