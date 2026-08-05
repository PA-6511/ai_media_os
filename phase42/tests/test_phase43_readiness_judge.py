from phase42.finalization_design.phase43_readiness_judge import judge_phase43_planning_readiness


def test_readiness_ready_only_on_pass_and_allow_phase43_planning_only() -> None:
    result = judge_phase43_planning_readiness(
        {"policy_status": "PASS"},
        selected_decision="ALLOW_PHASE43_PLANNING_ONLY",
    )
    assert result["readiness_status"] == "READY_FOR_PHASE43_PLANNING_ONLY"
    assert result["can_execute"] is False


def test_readiness_not_ready_otherwise() -> None:
    result = judge_phase43_planning_readiness(
        {"policy_status": "PASS"},
        selected_decision="REJECT",
    )
    assert result["readiness_status"] == "NOT_READY"
    assert result["can_execute"] is False
