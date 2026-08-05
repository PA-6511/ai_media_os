from phase34.final_review_design.manual_dry_run_execution_final_pre_execution_review_builder import (
    build_manual_dry_run_execution_final_pre_execution_review,
)


def test_final_pre_execution_review_fails_when_phase33_not_ready() -> None:
    result = build_manual_dry_run_execution_final_pre_execution_review(
        {"readiness_status": "NOT_READY", "can_execute": False}
    )
    assert result["status"] == "FAIL"


def test_final_pre_execution_review_fails_when_phase33_can_execute_true() -> None:
    result = build_manual_dry_run_execution_final_pre_execution_review(
        {"readiness_status": "READY_FOR_PHASE34_PLANNING_ONLY", "can_execute": True}
    )
    assert result["status"] == "FAIL"


def test_final_pre_execution_review_enforces_non_execute_flags() -> None:
    result = build_manual_dry_run_execution_final_pre_execution_review(
        {"readiness_status": "READY_FOR_PHASE34_PLANNING_ONLY", "can_execute": False}
    )
    assert result["status"] == "FINAL_PRE_EXECUTION_REVIEW_READY"
    assert result["mode"] == "DRY_RUN"
    assert result["can_execute"] is False
    assert result["execute_allowed"] is False
    assert result["max_files_to_execute"] == 1
