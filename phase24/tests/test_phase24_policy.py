from phase24.review.phase24_policy import evaluate_phase24_policy


def _base_review() -> dict:
    return {
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "max_files_to_execute": 1,
        "execute_allowed": False,
    }


def _base_decision() -> dict:
    return {
        "decision_options": ["GO_PHASE25_PLANNING_ONLY", "NO_GO"],
        "go_does_not_execute": True,
    }


def test_policy_fails_when_go_does_not_execute_false() -> None:
    decision = _base_decision()
    decision["go_does_not_execute"] = False
    result = evaluate_phase24_policy(_base_review(), decision)
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_max_files_invalid() -> None:
    review = _base_review()
    review["max_files_to_execute"] = 2
    result = evaluate_phase24_policy(review, _base_decision())
    assert result["policy_status"] == "FAIL"
