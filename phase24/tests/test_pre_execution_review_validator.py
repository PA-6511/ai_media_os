from phase24.review.pre_execution_review_validator import validate_pre_execution_review


def _base_review() -> dict:
    return {
        "phase": "24",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "review_scope": "single_file_pre_execution_review_only",
        "max_files_to_execute": 1,
        "execute_allowed": False,
        "status": "PRE_EXECUTION_REVIEW_READY",
    }


def test_validator_fails_on_mode_violation() -> None:
    review = _base_review()
    review["mode"] = "LIVE"
    result = validate_pre_execution_review(review)
    assert result["status"] == "FAIL"


def test_validator_fails_on_execute_allowed_true() -> None:
    review = _base_review()
    review["execute_allowed"] = True
    result = validate_pre_execution_review(review)
    assert result["status"] == "FAIL"
