from phase67.preparation_evidence_design.phase68_readiness_judge import (
    judge_phase68_planning_readiness,
)


def test_readiness_ready_on_pass_and_allow_phase68_planning_only() -> None:
    result = judge_phase68_planning_readiness(
        {"policy_status": "PASS"},
        selected_decision="ALLOW_PHASE68_PLANNING_ONLY",
    )
    assert result["readiness_status"] == "READY_FOR_PHASE68_PLANNING_ONLY"
    assert result["can_execute"] is False
    assert result["execute_allowed"] is False


def test_readiness_not_ready_on_reject() -> None:
    result = judge_phase68_planning_readiness(
        {"policy_status": "PASS"},
        selected_decision="REJECT",
    )
    assert result["readiness_status"] == "NOT_READY"
    assert result["can_execute"] is False
    assert result["execute_allowed"] is False
