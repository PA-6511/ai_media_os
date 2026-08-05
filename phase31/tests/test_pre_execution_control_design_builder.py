from phase31.control_design.pre_execution_control_design_builder import (
    build_pre_execution_control_design,
)


def test_control_design_fails_when_phase30_not_ready() -> None:
    result = build_pre_execution_control_design(
        {"readiness_status": "NOT_READY", "can_execute": False}
    )
    assert result["status"] == "FAIL"


def test_control_design_fails_when_phase30_can_execute_true() -> None:
    result = build_pre_execution_control_design(
        {"readiness_status": "READY_FOR_PHASE31_PLANNING_ONLY", "can_execute": True}
    )
    assert result["status"] == "FAIL"


def test_control_design_enforces_non_execute_flags() -> None:
    result = build_pre_execution_control_design(
        {"readiness_status": "READY_FOR_PHASE31_PLANNING_ONLY", "can_execute": False}
    )
    assert result["status"] == "PRE_EXECUTION_CONTROL_DESIGN_READY"
    assert result["mode"] == "DRY_RUN"
    assert result["execute_allowed"] is False
    assert result["can_execute"] is False
    assert result["max_files_to_execute"] == 1
