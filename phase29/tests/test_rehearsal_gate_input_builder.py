from phase29.gate.rehearsal_gate_input_builder import build_rehearsal_gate_input


def test_gate_input_fails_when_phase28_not_ready() -> None:
    result = build_rehearsal_gate_input(
        {"readiness_status": "NOT_READY", "can_execute": False}
    )
    assert result["status"] == "FAIL"


def test_gate_input_fails_when_phase28_can_execute_true() -> None:
    result = build_rehearsal_gate_input(
        {"readiness_status": "READY_FOR_PHASE29_PLANNING_ONLY", "can_execute": True}
    )
    assert result["status"] == "FAIL"


def test_gate_input_keeps_single_file_limit_and_execute_disabled() -> None:
    result = build_rehearsal_gate_input(
        {"readiness_status": "READY_FOR_PHASE29_PLANNING_ONLY", "can_execute": False}
    )
    assert result["status"] == "REHEARSAL_GATE_INPUT_READY"
    assert result["max_files_to_execute"] == 1
    assert result["execute_allowed"] is False
