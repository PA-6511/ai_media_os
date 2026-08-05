from phase25.planning.phase26_readiness_judge import judge_phase26_planning_readiness


def test_readiness_ready_only_when_policy_pass() -> None:
    result = judge_phase26_planning_readiness({"policy_status": "PASS"})
    assert result["readiness_status"] == "READY_FOR_PHASE26_PLANNING_ONLY"
    assert result["can_execute"] is False


def test_readiness_not_ready_when_policy_fail() -> None:
    result = judge_phase26_planning_readiness({"policy_status": "FAIL"})
    assert result["readiness_status"] == "NOT_READY"
    assert result["can_execute"] is False
