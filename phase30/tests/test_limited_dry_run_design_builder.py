from phase30.execution_design.limited_dry_run_design_builder import (
    build_limited_dry_run_design,
)


def test_design_fails_when_phase29_not_ready() -> None:
    result = build_limited_dry_run_design(
        {"readiness_status": "NOT_READY", "can_execute": False}
    )
    assert result["status"] == "FAIL"


def test_design_fails_when_phase29_can_execute_true() -> None:
    result = build_limited_dry_run_design(
        {"readiness_status": "READY_FOR_PHASE30_PLANNING_ONLY", "can_execute": True}
    )
    assert result["status"] == "FAIL"


def test_design_keeps_single_file_limit_and_execute_disabled() -> None:
    result = build_limited_dry_run_design(
        {"readiness_status": "READY_FOR_PHASE30_PLANNING_ONLY", "can_execute": False}
    )
    assert result["status"] == "LIMITED_DRY_RUN_DESIGN_READY"
    assert result["max_files_to_execute"] == 1
    assert result["execute_allowed"] is False
    assert result["sandbox_scope_required"] is True
