from phase28.gate.manual_dry_run_gate_builder import build_manual_dry_run_gate


def test_gate_fails_when_phase27_not_ready() -> None:
    result = build_manual_dry_run_gate(
        {"readiness_status": "NOT_READY", "can_execute": False}
    )
    assert result["status"] == "FAIL"


def test_gate_fails_when_phase27_can_execute_true() -> None:
    result = build_manual_dry_run_gate(
        {"readiness_status": "READY_FOR_PHASE28_PLANNING_ONLY", "can_execute": True}
    )
    assert result["status"] == "FAIL"


def test_gate_keeps_single_file_limit_and_execute_disabled() -> None:
    result = build_manual_dry_run_gate(
        {"readiness_status": "READY_FOR_PHASE28_PLANNING_ONLY", "can_execute": False}
    )
    assert result["status"] == "MANUAL_DRY_RUN_GATE_READY"
    assert result["max_files_to_execute"] == 1
    assert result["execute_allowed"] is False
