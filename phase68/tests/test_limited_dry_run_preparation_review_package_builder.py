from phase68.preparation_review_design.limited_dry_run_preparation_review_package_builder import (
    build_limited_dry_run_preparation_review_package,
)


def _phase67_ready_report() -> dict:
    return {
        "readiness_status": "READY_FOR_PHASE68_PLANNING_ONLY",
        "can_execute": False,
        "execute_allowed": False,
    }


def test_package_fails_when_readiness_not_met() -> None:
    data = _phase67_ready_report()
    data["readiness_status"] = "NOT_READY"
    result = build_limited_dry_run_preparation_review_package(data)
    assert result["status"] == "FAIL"


def test_package_fails_when_can_execute_true() -> None:
    data = _phase67_ready_report()
    data["can_execute"] = True
    result = build_limited_dry_run_preparation_review_package(data)
    assert result["status"] == "FAIL"


def test_package_fails_when_execute_allowed_true() -> None:
    data = _phase67_ready_report()
    data["execute_allowed"] = True
    result = build_limited_dry_run_preparation_review_package(data)
    assert result["status"] == "FAIL"


def test_package_ready_with_valid_input() -> None:
    result = build_limited_dry_run_preparation_review_package(_phase67_ready_report())
    assert result["status"] == "PREPARATION_REVIEW_PACKAGE_READY"
    assert result["can_execute"] is False
    assert result["execute_allowed"] is False
