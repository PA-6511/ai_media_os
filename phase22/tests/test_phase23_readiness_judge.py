from phase22.design.phase23_readiness_judge import judge_phase23_planning_readiness


def test_readiness_ready_only_on_policy_pass() -> None:
    result = judge_phase23_planning_readiness({"policy_status": "PASS"})
    assert result["readiness_status"] == "READY_FOR_PHASE23_PLANNING_ONLY"
    assert result["can_apply"] is False


def test_readiness_not_ready_on_policy_fail() -> None:
    result = judge_phase23_planning_readiness({"policy_status": "FAIL"})
    assert result["readiness_status"] == "NOT_READY"
    assert result["can_apply"] is False
