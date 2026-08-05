from phase34.final_review_design.manual_gate_final_pre_execution_review_builder import (
    build_manual_gate_final_pre_execution_review,
)


def test_manual_gate_final_pre_execution_review_allows_phase35_planning_only() -> None:
    gate = build_manual_gate_final_pre_execution_review(
        {"status": "FINAL_PRE_EXECUTION_REVIEW_READY"}
    )
    assert gate["status"] == "MANUAL_GATE_FINAL_PRE_EXECUTION_REVIEW_READY"
    assert gate["allow_does_not_execute"] is True
    assert "ALLOW_PHASE35_PLANNING_ONLY" in gate["allowed_decisions"]
