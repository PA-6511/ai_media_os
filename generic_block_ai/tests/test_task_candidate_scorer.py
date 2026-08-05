from generic_block_ai.app.safety_guard import GuardDecision
from generic_block_ai.app.task_candidate_scorer import score_task_candidates


def test_score_task_candidates_is_deterministic_and_sorted() -> None:
    requested_actions = [
        {"type": "collect_data", "target": "source_a"},
        {"type": "generate_report", "target": "weekly"},
        {"type": "propose_deployment_plan", "target": "ops"},
    ]
    guard_decision = GuardDecision(
        allowed_actions=[requested_actions[0], requested_actions[1]],
        blocked_actions=[],
        needs_review_actions=[requested_actions[2]],
        reason_codes=[],
        warnings=[],
    )

    first = score_task_candidates(requested_actions, guard_decision)
    second = score_task_candidates(requested_actions, guard_decision)

    assert first == second
    assert [item["priority_score"] for item in first] == sorted(
        [item["priority_score"] for item in first], reverse=True
    )


def test_score_task_candidates_stays_in_score_bounds() -> None:
    requested_actions = [
        {"type": "collect_data", "target": "source_a"},
        {"type": "delete_block", "target": "generic_block"},
        {"type": "propose_deployment_plan", "target": "ops"},
    ]
    guard_decision = GuardDecision(
        allowed_actions=[requested_actions[0]],
        blocked_actions=[requested_actions[1]],
        needs_review_actions=[requested_actions[2]],
        reason_codes=[],
        warnings=[],
    )

    scored = score_task_candidates(requested_actions, guard_decision)
    for item in scored:
        for key in ("impact_score", "risk_score", "confidence_score", "priority_score"):
            assert 0 <= item[key] <= 100

    by_type = {item["action_type"]: item for item in scored}
    assert by_type["delete_block"]["classification"] == "block"
    assert by_type["propose_deployment_plan"]["classification"] == "needs_review"
    assert by_type["collect_data"]["classification"] == "allow"