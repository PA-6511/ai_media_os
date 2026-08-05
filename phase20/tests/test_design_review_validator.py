from phase20.review.design_review_validator import validate_design_review_package


def test_validator_fails_on_missing_keys() -> None:
    result = validate_design_review_package({"phase": "20"})
    assert result["status"] == "FAIL"
    assert len(result["missing_keys"]) > 0


def test_validator_passes_on_complete_package() -> None:
    package = {
        "phase": "20",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "source_phase19_result": {},
        "review_checklist": [],
        "risk_summary": [],
        "status": "REVIEW_READY",
    }
    result = validate_design_review_package(package)
    assert result["status"] == "PASS"
