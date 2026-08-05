from phase20.review.release_candidate_policy import evaluate_release_candidate_policy


def _base_package() -> dict:
    return {
        "phase": "20",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "apply_instruction": "DO_NOT_APPLY_IN_PHASE20",
        "notes": "safe candidate",
    }


def test_policy_fails_when_mode_invalid() -> None:
    rc = _base_package()
    rc["mode"] = "LIVE"
    result = evaluate_release_candidate_policy(rc)
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_human_approval_required_false() -> None:
    rc = _base_package()
    rc["human_approval_required"] = False
    result = evaluate_release_candidate_policy(rc)
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_apply_instruction_invalid() -> None:
    rc = _base_package()
    rc["apply_instruction"] = "APPLY_NOW"
    result = evaluate_release_candidate_policy(rc)
    assert result["policy_status"] == "FAIL"


def test_policy_detects_forbidden_terms() -> None:
    rc = _base_package()
    rc["notes"] = "contains DEPLOY directive"
    result = evaluate_release_candidate_policy(rc)
    assert result["policy_status"] == "FAIL"
    assert any(reason.startswith("forbidden_term_detected:DEPLOY") for reason in result["reasons"])
