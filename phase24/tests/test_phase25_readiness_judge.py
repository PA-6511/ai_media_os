from phase24.review.phase25_readiness_judge import judge_phase25_planning_readiness


def test_readiness_ready_only_on_pass_and_go_planning_only() -> None:
    result = judge_phase25_planning_readiness(
        {"status": "PASS"},
        {"policy_status": "PASS"},
        selected_decision="GO_PHASE25_PLANNING_ONLY",
    )
    assert result["readiness_status"] == "READY_FOR_PHASE25_PLANNING_ONLY"
    assert result["can_execute"] is False


def test_readiness_not_ready_otherwise() -> None:
    result = judge_phase25_planning_readiness(
        {"status": "PASS"},
        {"policy_status": "PASS"},
        selected_decision="NO_GO",
    )
    assert result["readiness_status"] == "NOT_READY"
    assert result["can_execute"] is False
