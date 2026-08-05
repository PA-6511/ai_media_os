from phase52.go_live_review_design.manual_dry_run_execution_go_live_review_package_builder import (
    build_manual_dry_run_execution_go_live_review_package,
)


def test_go_live_review_package_fails_when_phase51_not_ready() -> None:
    result = build_manual_dry_run_execution_go_live_review_package(
        {"readiness_status": "NOT_READY", "can_execute": False}
    )
    assert result["status"] == "FAIL"


def test_go_live_review_package_fails_when_phase51_can_execute_true() -> None:
    result = build_manual_dry_run_execution_go_live_review_package(
        {"readiness_status": "READY_FOR_PHASE52_PLANNING_ONLY", "can_execute": True}
    )
    assert result["status"] == "FAIL"


def test_go_live_review_package_enforces_non_execute_flags() -> None:
    result = build_manual_dry_run_execution_go_live_review_package(
        {"readiness_status": "READY_FOR_PHASE52_PLANNING_ONLY", "can_execute": False}
    )
    assert result["status"] == "GO_LIVE_REVIEW_PACKAGE_READY"
    assert result["mode"] == "DRY_RUN"
    assert result["max_files_to_execute"] == 1
    assert result["can_execute"] is False
    assert result["execute_allowed"] is False
