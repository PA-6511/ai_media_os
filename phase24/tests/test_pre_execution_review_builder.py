from phase24.review.pre_execution_review_builder import build_pre_execution_review


def test_review_fails_when_phase23_not_ready() -> None:
    result = build_pre_execution_review(
        {"readiness_status": "NOT_READY", "can_execute": False}
    )
    assert result["status"] == "FAIL"


def test_review_fails_when_phase23_can_execute_true() -> None:
    result = build_pre_execution_review(
        {"readiness_status": "READY_FOR_PHASE24_PLANNING_ONLY", "can_execute": True}
    )
    assert result["status"] == "FAIL"


def test_review_has_single_file_limit_and_execute_disabled() -> None:
    result = build_pre_execution_review(
        {"readiness_status": "READY_FOR_PHASE24_PLANNING_ONLY", "can_execute": False}
    )
    assert result["status"] == "PRE_EXECUTION_REVIEW_READY"
    assert result["max_files_to_execute"] == 1
    assert result["execute_allowed"] is False
