from phase27.decision.go_nogo_decision_policy import evaluate_go_nogo_decision_policy


def _base_input() -> dict:
    return {
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "max_files_to_execute": 1,
        "execute_allowed": False,
    }


def _base_criteria() -> dict:
    return {
        "go_does_not_execute": True,
        "status": "GO_NOGO_CRITERIA_READY",
    }


def test_policy_fails_when_max_files_invalid() -> None:
    go_input = _base_input()
    go_input["max_files_to_execute"] = 2
    result = evaluate_go_nogo_decision_policy(go_input, _base_criteria())
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_execute_allowed_true() -> None:
    go_input = _base_input()
    go_input["execute_allowed"] = True
    result = evaluate_go_nogo_decision_policy(go_input, _base_criteria())
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_go_does_not_execute_false() -> None:
    criteria = _base_criteria()
    criteria["go_does_not_execute"] = False
    result = evaluate_go_nogo_decision_policy(_base_input(), criteria)
    assert result["policy_status"] == "FAIL"
