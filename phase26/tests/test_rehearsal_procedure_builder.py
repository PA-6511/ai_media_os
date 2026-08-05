from phase26.rehearsal.rehearsal_procedure_builder import build_rehearsal_procedure


def test_procedure_fails_when_phase25_not_ready() -> None:
    result = build_rehearsal_procedure(
        {"readiness_status": "NOT_READY", "can_execute": False}
    )
    assert result["status"] == "FAIL"


def test_procedure_fails_when_phase25_can_execute_true() -> None:
    result = build_rehearsal_procedure(
        {"readiness_status": "READY_FOR_PHASE26_PLANNING_ONLY", "can_execute": True}
    )
    assert result["status"] == "FAIL"


def test_procedure_keeps_single_file_limit_and_execute_disabled() -> None:
    result = build_rehearsal_procedure(
        {"readiness_status": "READY_FOR_PHASE26_PLANNING_ONLY", "can_execute": False}
    )
    assert result["status"] == "REHEARSAL_PROCEDURE_READY"
    assert result["max_files_to_execute"] == 1
    assert result["execute_allowed"] is False
