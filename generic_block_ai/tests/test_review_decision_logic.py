from generic_block_ai.app.review_decision_logic import build_recommended_decision


def test_recommended_decision_approve_when_ready() -> None:
    result = {"status": "success"}
    metrics = {
        "review_readiness": "ready",
        "details": {"proposal_validation_result": "PASS"},
    }

    recommendation = build_recommended_decision(result, metrics)
    assert recommendation["recommended_decision"] == "RECOMMEND_APPROVE_DRY_RUN_ONLY"
    assert recommendation["safeguards"]["actual_auto_execute"] is False
    assert recommendation["safeguards"]["external_write_executed"] is False


def test_recommended_decision_reject_on_validation_fail() -> None:
    result = {"status": "success"}
    metrics = {
        "review_readiness": "needs_attention",
        "details": {"proposal_validation_result": "FAIL"},
    }

    recommendation = build_recommended_decision(result, metrics)
    assert recommendation["recommended_decision"] == "RECOMMEND_REJECT"


def test_recommended_decision_blocked_by_status() -> None:
    result = {"status": "blocked"}
    metrics = {
        "review_readiness": "ready",
        "details": {"proposal_validation_result": "PASS"},
    }

    recommendation = build_recommended_decision(result, metrics)
    assert recommendation["recommended_decision"] == "BLOCKED_BY_POLICY"


def test_recommended_decision_respects_policy_override() -> None:
    result = {"status": "success"}
    metrics = {
        "review_readiness": "needs_attention",
        "details": {"proposal_validation_result": "PASS"},
    }

    recommendation = build_recommended_decision(
        result,
        metrics,
        policy_review_decision={"approve_on_readiness": ["ready", "needs_attention"]},
    )
    assert recommendation["recommended_decision"] == "RECOMMEND_APPROVE_DRY_RUN_ONLY"