from phase66.go_no_go_review.phase66_go_no_go_gate import judge_phase66_go_no_go


def _phase65_pass_report() -> dict:
    return {
        "completion_status": "PASS",
        "safety_boundaries": {
            "dry_run_fixed": True,
            "human_approval_required": True,
            "can_execute": False,
            "execute_allowed": False,
            "max_files_to_execute": 1,
            "sandbox_scope_required": True,
            "single_file_scope_required": True,
            "does_not_execute_guards": True,
        },
    }


def test_not_approved_when_phase65_not_pass() -> None:
    report = _phase65_pass_report()
    report["completion_status"] = "FAIL"
    result = judge_phase66_go_no_go(report, "ALLOW_LIMITED_DRY_RUN_PREPARATION_ONLY")
    assert result["review_status"] == "NOT_APPROVED"
    assert result["go_no_go"] == "NO_GO"


def test_not_approved_when_safety_boundary_broken() -> None:
    report = _phase65_pass_report()
    report["safety_boundaries"]["execute_allowed"] = True
    result = judge_phase66_go_no_go(report, "ALLOW_LIMITED_DRY_RUN_PREPARATION_ONLY")
    assert result["review_status"] == "NOT_APPROVED"
    assert result["go_no_go"] == "NO_GO"


def test_not_approved_when_decision_invalid() -> None:
    result = judge_phase66_go_no_go(_phase65_pass_report(), "ALLOW_EXECUTION")
    assert result["review_status"] == "NOT_APPROVED"
    assert result["go_no_go"] == "NO_GO"


def test_go_when_allow_limited_dry_run_preparation_only() -> None:
    result = judge_phase66_go_no_go(
        _phase65_pass_report(),
        "ALLOW_LIMITED_DRY_RUN_PREPARATION_ONLY",
    )
    assert result["review_status"] == "APPROVED"
    assert result["go_no_go"] == "GO"
    assert result["can_execute"] is False
    assert result["execute_allowed"] is False


def test_no_go_when_decision_is_no_go() -> None:
    result = judge_phase66_go_no_go(_phase65_pass_report(), "NO_GO")
    assert result["review_status"] == "APPROVED"
    assert result["go_no_go"] == "NO_GO"
    assert result["can_execute"] is False
    assert result["execute_allowed"] is False
