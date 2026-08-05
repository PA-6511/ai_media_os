from phase68.preparation_review_design.phase69_readiness_judge import (
    judge_phase69_planning_readiness,
)


def test_readiness_ready_on_pass_and_allow_phase69_planning_only() -> None:
    result = judge_phase69_planning_readiness(
        {"policy_status": "PASS"},
        selected_decision="ALLOW_PHASE69_PLANNING_ONLY",
    )
    assert result["readiness_status"] == "READY_FOR_PHASE69_PLANNING_ONLY"
    assert result["can_execute"] is False
    assert result["execute_allowed"] is False


def test_readiness_not_ready_on_reject() -> None:
    result = judge_phase69_planning_readiness(
        {"policy_status": "PASS"},
        selected_decision="REJECT",
    )
    assert result["readiness_status"] == "NOT_READY"
    assert result["can_execute"] is False
    assert result["execute_allowed"] is False
