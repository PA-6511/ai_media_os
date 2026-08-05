from phase27.decision.phase28_readiness_judge import judge_phase28_planning_readiness


def test_readiness_ready_only_on_pass_and_go_planning_only() -> None:
    result = judge_phase28_planning_readiness(
        {"policy_status": "PASS"},
        selected_decision="GO_PHASE28_PLANNING_ONLY",
    )
    assert result["readiness_status"] == "READY_FOR_PHASE28_PLANNING_ONLY"
    assert result["can_execute"] is False


def test_readiness_not_ready_otherwise() -> None:
    result = judge_phase28_planning_readiness(
        {"policy_status": "PASS"},
        selected_decision="NO_GO",
    )
    assert result["readiness_status"] == "NOT_READY"
    assert result["can_execute"] is False
