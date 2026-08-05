from phase55.final_readiness_design.phase56_readiness_judge import judge_phase56_planning_readiness


def test_readiness_ready_on_pass_and_allow_phase56_planning_only() -> None:
    result = judge_phase56_planning_readiness(
        {"policy_status": "PASS"},
        selected_decision="ALLOW_PHASE56_PLANNING_ONLY",
    )
    assert result["readiness_status"] == "READY_FOR_PHASE56_PLANNING_ONLY"
    assert result["can_execute"] is False


def test_readiness_not_ready_on_reject() -> None:
    result = judge_phase56_planning_readiness(
        {"policy_status": "PASS"},
        selected_decision="REJECT",
    )
    assert result["readiness_status"] == "NOT_READY"
    assert result["can_execute"] is False


def test_can_execute_always_false() -> None:
    for decision in ["ALLOW_PHASE56_PLANNING_ONLY", "REJECT", None]:
        result = judge_phase56_planning_readiness({"policy_status": "PASS"}, selected_decision=decision)
        assert result["can_execute"] is False
