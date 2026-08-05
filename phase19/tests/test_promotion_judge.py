from phase19.evaluation.promotion_judge import judge_promotion_readiness


def test_promotion_ready_for_phase20_design_when_all_pass() -> None:
    result = judge_promotion_readiness(
        {"quality_status": "PASS"},
        {"safety_status": "PASS"},
        {"rollback_status": "PASS"},
    )
    assert result["promotion_status"] == "READY_FOR_PHASE20_DESIGN"
    assert result["can_promote"] is False


def test_promotion_not_ready_when_any_non_pass() -> None:
    result = judge_promotion_readiness(
        {"quality_status": "WARN"},
        {"safety_status": "PASS"},
        {"rollback_status": "PASS"},
    )
    assert result["promotion_status"] == "NOT_READY"
    assert result["can_promote"] is False
