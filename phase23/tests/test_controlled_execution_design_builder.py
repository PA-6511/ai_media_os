from phase23.execution_design.controlled_execution_design_builder import (
    build_controlled_execution_design,
)


def test_design_fails_when_phase22_not_ready() -> None:
    result = build_controlled_execution_design(
        {"readiness_status": "NOT_READY", "can_apply": False}
    )
    assert result["status"] == "FAIL"


def test_design_fails_when_phase22_can_apply_true() -> None:
    result = build_controlled_execution_design(
        {"readiness_status": "READY_FOR_PHASE23_PLANNING_ONLY", "can_apply": True}
    )
    assert result["status"] == "FAIL"


def test_design_enforces_single_file_and_execute_disabled() -> None:
    result = build_controlled_execution_design(
        {
            "readiness_status": "READY_FOR_PHASE23_PLANNING_ONLY",
            "can_apply": False,
            "planned_target_files": ["a", "b"],
        }
    )
    assert result["status"] == "CONTROLLED_EXECUTION_DESIGN_READY"
    assert result["max_files_to_execute"] == 1
    assert len(result["planned_target_files"]) <= 1
    assert result["execute_allowed"] is False
