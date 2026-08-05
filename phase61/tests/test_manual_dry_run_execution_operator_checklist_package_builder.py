from phase61.operator_checklist_design.manual_dry_run_execution_operator_checklist_package_builder import (
    build_manual_dry_run_execution_operator_checklist_package,
)


def test_operator_checklist_package_fails_when_phase60_not_ready() -> None:
    result = build_manual_dry_run_execution_operator_checklist_package(
        {"readiness_status": "NOT_READY", "can_execute": False}
    )
    assert result["status"] == "FAIL"


def test_operator_checklist_package_fails_when_phase60_can_execute_true() -> None:
    result = build_manual_dry_run_execution_operator_checklist_package(
        {"readiness_status": "READY_FOR_PHASE61_PLANNING_ONLY", "can_execute": True}
    )
    assert result["status"] == "FAIL"


def test_operator_checklist_package_enforces_non_execute_flags() -> None:
    result = build_manual_dry_run_execution_operator_checklist_package(
        {"readiness_status": "READY_FOR_PHASE61_PLANNING_ONLY", "can_execute": False}
    )
    assert result["status"] == "OPERATOR_CHECKLIST_PACKAGE_READY"
    assert result["mode"] == "DRY_RUN"
    assert result["max_files_to_execute"] == 1
    assert result["can_execute"] is False
    assert result["execute_allowed"] is False
