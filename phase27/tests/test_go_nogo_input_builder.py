from phase27.decision.go_nogo_input_builder import build_go_nogo_input


def test_input_fails_when_phase26_not_ready() -> None:
    result = build_go_nogo_input(
        {"readiness_status": "NOT_READY", "can_execute": False}
    )
    assert result["status"] == "FAIL"


def test_input_fails_when_phase26_can_execute_true() -> None:
    result = build_go_nogo_input(
        {"readiness_status": "READY_FOR_PHASE27_PLANNING_ONLY", "can_execute": True}
    )
    assert result["status"] == "FAIL"


def test_input_keeps_single_file_limit_and_execute_disabled() -> None:
    result = build_go_nogo_input(
        {"readiness_status": "READY_FOR_PHASE27_PLANNING_ONLY", "can_execute": False}
    )
    assert result["status"] == "GO_NOGO_INPUT_READY"
    assert result["max_files_to_execute"] == 1
    assert result["execute_allowed"] is False
