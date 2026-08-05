from phase68.preparation_review_design.manual_review_gate_builder import (
    build_manual_review_gate,
)


def test_manual_review_gate_allows_phase69_planning_only() -> None:
    gate = build_manual_review_gate({"status": "PREPARATION_REVIEW_PACKAGE_READY"})
    assert gate["gate_required"] is True
    assert "ALLOW_PHASE69_PLANNING_ONLY" in gate["allowed_decisions"]
    assert gate["manual_review_gate_does_not_execute"] is True
