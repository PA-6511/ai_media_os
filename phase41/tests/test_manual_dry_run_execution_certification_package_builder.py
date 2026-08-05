from phase41.certification_design.manual_dry_run_execution_certification_package_builder import (
    build_manual_dry_run_execution_certification_package,
)


def test_certification_package_fails_when_phase40_not_ready() -> None:
    result = build_manual_dry_run_execution_certification_package(
        {"readiness_status": "NOT_READY", "can_execute": False}
    )
    assert result["status"] == "FAIL"


def test_certification_package_fails_when_phase40_can_execute_true() -> None:
    result = build_manual_dry_run_execution_certification_package(
        {"readiness_status": "READY_FOR_PHASE41_PLANNING_ONLY", "can_execute": True}
    )
    assert result["status"] == "FAIL"


def test_certification_package_enforces_non_execute_flags() -> None:
    result = build_manual_dry_run_execution_certification_package(
        {"readiness_status": "READY_FOR_PHASE41_PLANNING_ONLY", "can_execute": False}
    )
    assert result["status"] == "MANUAL_DRY_RUN_EXECUTION_CERTIFICATION_PACKAGE_READY"
    assert result["mode"] == "DRY_RUN"
    assert result["can_execute"] is False
    assert result["execute_allowed"] is False
    assert result["max_files_to_execute"] == 1
