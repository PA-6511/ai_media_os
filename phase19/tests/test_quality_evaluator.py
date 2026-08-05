from phase19.evaluation.quality_evaluator import evaluate_quality


def test_quality_pass_when_execution_and_verify_pass() -> None:
    result = evaluate_quality(
        {
            "execution_status": "PASS",
            "verify_status": "PASS",
            "applied_files": ["a"],
            "blocked_files": [],
            "findings": [],
        }
    )
    assert result["quality_status"] == "PASS"


def test_quality_warn_when_blocked_files_exist() -> None:
    result = evaluate_quality(
        {
            "execution_status": "PASS",
            "verify_status": "PASS",
            "applied_files": ["a"],
            "blocked_files": ["x"],
            "findings": [],
        }
    )
    assert result["quality_status"] == "WARN"


def test_quality_fail_when_execution_fail() -> None:
    result = evaluate_quality(
        {
            "execution_status": "FAIL",
            "verify_status": "PASS",
            "applied_files": [],
            "blocked_files": [],
            "findings": [],
        }
    )
    assert result["quality_status"] == "FAIL"
