from phase26.rehearsal.phase26_policy import evaluate_phase26_policy


def _base_procedure() -> dict:
    return {
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "max_files_to_execute": 1,
        "execute_allowed": False,
    }


def test_policy_fails_when_max_files_invalid() -> None:
    procedure = _base_procedure()
    procedure["max_files_to_execute"] = 2
    result = evaluate_phase26_policy(
        procedure,
        {"status": "OBSERVATION_POINTS_READY"},
        {"status": "ABORT_CONDITIONS_READY"},
        {"evidence_review_required": True, "evidence_does_not_execute": True},
    )
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_execute_allowed_true() -> None:
    procedure = _base_procedure()
    procedure["execute_allowed"] = True
    result = evaluate_phase26_policy(
        procedure,
        {"status": "OBSERVATION_POINTS_READY"},
        {"status": "ABORT_CONDITIONS_READY"},
        {"evidence_review_required": True, "evidence_does_not_execute": True},
    )
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_evidence_does_not_execute_false() -> None:
    result = evaluate_phase26_policy(
        _base_procedure(),
        {"status": "OBSERVATION_POINTS_READY"},
        {"status": "ABORT_CONDITIONS_READY"},
        {"evidence_review_required": True, "evidence_does_not_execute": False},
    )
    assert result["policy_status"] == "FAIL"
