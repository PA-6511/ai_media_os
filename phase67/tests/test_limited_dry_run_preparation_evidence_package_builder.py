from phase67.preparation_evidence_design.limited_dry_run_preparation_evidence_package_builder import (
    build_limited_dry_run_preparation_evidence_package,
)


def _phase66_go_report() -> dict:
    return {
        "review_status": "APPROVED",
        "go_no_go": "GO",
        "selected_decision": "ALLOW_LIMITED_DRY_RUN_PREPARATION_ONLY",
        "can_execute": False,
        "execute_allowed": False,
    }


def test_package_fails_when_review_not_approved() -> None:
    data = _phase66_go_report()
    data["review_status"] = "NOT_APPROVED"
    result = build_limited_dry_run_preparation_evidence_package(data)
    assert result["status"] == "FAIL"


def test_package_fails_when_go_no_go_not_go() -> None:
    data = _phase66_go_report()
    data["go_no_go"] = "NO_GO"
    result = build_limited_dry_run_preparation_evidence_package(data)
    assert result["status"] == "FAIL"


def test_package_fails_when_execute_allowed_true() -> None:
    data = _phase66_go_report()
    data["execute_allowed"] = True
    result = build_limited_dry_run_preparation_evidence_package(data)
    assert result["status"] == "FAIL"


def test_package_ready_with_valid_input() -> None:
    result = build_limited_dry_run_preparation_evidence_package(_phase66_go_report())
    assert result["status"] == "PREPARATION_EVIDENCE_PACKAGE_READY"
    assert result["can_execute"] is False
    assert result["execute_allowed"] is False
