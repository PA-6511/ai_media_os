from phase24.review.go_nogo_decision_designer import design_go_nogo_decision


def test_decision_design_has_non_execute_guard() -> None:
    result = design_go_nogo_decision({"status": "PRE_EXECUTION_REVIEW_READY"})
    assert result["status"] == "GO_NOGO_DECISION_READY"
    assert result["go_does_not_execute"] is True
    assert "GO_PHASE25_PLANNING_ONLY" in result["decision_options"]
