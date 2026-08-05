from phase27.decision.go_nogo_criteria_builder import build_go_nogo_criteria


def test_criteria_contains_non_execute_guard() -> None:
    result = build_go_nogo_criteria({"status": "GO_NOGO_INPUT_READY"})
    assert result["status"] == "GO_NOGO_CRITERIA_READY"
    assert result["go_does_not_execute"] is True
    assert result["go_option"] == "GO_PHASE28_PLANNING_ONLY"
