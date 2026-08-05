from phase21.planning.phase22_readiness_judge import judge_phase22_readiness


def test_readiness_ready_only_when_validation_and_policy_pass() -> None:
    result = judge_phase22_readiness({"status": "PASS"}, {"policy_status": "PASS"})
    assert result["readiness_status"] == "READY_FOR_PHASE22_PLANNING_ONLY"
    assert result["can_apply"] is False


def test_readiness_not_ready_when_any_non_pass() -> None:
    result = judge_phase22_readiness({"status": "FAIL"}, {"policy_status": "PASS"})
    assert result["readiness_status"] == "NOT_READY"
    assert result["can_apply"] is False
