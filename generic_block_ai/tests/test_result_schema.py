import pytest

from generic_block_ai.app.result_schema import build_block_result


def test_build_block_result_success() -> None:
    result = build_block_result(
        status="success",
        decision="human_review",
        summary="ok",
        risk_level="low",
        needs_approval=True,
        mode="dry_run",
        actual_execution=False,
        actions=[],
        blocked_actions=[],
        needs_review_actions=[],
            task_candidates=[
                {
                    "candidate_id": "candidate_1",
                    "action_type": "collect_data",
                    "classification": "allow",
                    "impact_score": 55,
                    "risk_score": 25,
                    "confidence_score": 85,
                    "priority_score": 68,
                    "action": {"type": "collect_data", "target": "source_a"},
                }
            ],
            rejected_task_candidates=[],
        reason_codes=[
            {
                "action_type": "collect_data",
                "classification": "allow",
                "reason": "capability_enabled",
            }
        ],
        review_required_fields=["type", "target"],
        warnings=[],
        errors=[],
        block_id="generic_block",
        version="0.1.0",
    )
    assert result["status"] == "success"
    assert result["decision"] == "human_review"
    assert result["actual_execution"] is False
    assert result["task_candidates"][0]["priority_score"] == 68
    assert result["reason_codes"][0]["classification"] == "allow"


def test_build_block_result_rejects_non_dry_run() -> None:
    with pytest.raises(ValueError):
        build_block_result(
            status="success",
            decision="decision",
            summary="bad",
            risk_level="low",
            needs_approval=False,
            mode="real_run",
            actual_execution=False,
            actions=[],
            blocked_actions=[],
            needs_review_actions=[],
            task_candidates=[],
            rejected_task_candidates=[],
            reason_codes=[],
            review_required_fields=[],
            warnings=[],
            errors=[],
            block_id="generic_block",
            version="0.1.0",
        )


def test_build_block_result_rejects_invalid_reason_code() -> None:
    with pytest.raises(ValueError, match=r"reason_codes\[\]\.classification is required"):
        build_block_result(
            status="success",
            decision="human_review",
            summary="bad reason code",
            risk_level="low",
            needs_approval=True,
            mode="dry_run",
            actual_execution=False,
            actions=[],
            blocked_actions=[],
            needs_review_actions=[],
            task_candidates=[],
            rejected_task_candidates=[],
            reason_codes=[{"action_type": "x", "classification": "", "reason": "why"}],
            review_required_fields=[],
            warnings=[],
            errors=[],
            block_id="generic_block",
            version="0.1.0",
        )


def test_build_block_result_rejects_out_of_range_task_score() -> None:
    with pytest.raises(ValueError, match=r"task_candidates\[\]\.priority_score must be between 0 and 100"):
        build_block_result(
            status="success",
            decision="human_review",
            summary="bad score",
            risk_level="low",
            needs_approval=True,
            mode="dry_run",
            actual_execution=False,
            actions=[],
            blocked_actions=[],
            needs_review_actions=[],
            task_candidates=[
                {
                    "candidate_id": "candidate_1",
                    "action_type": "collect_data",
                    "classification": "allow",
                    "impact_score": 55,
                    "risk_score": 25,
                    "confidence_score": 85,
                    "priority_score": 130,
                    "action": {"type": "collect_data", "target": "source_a"},
                }
            ],
            rejected_task_candidates=[],
            reason_codes=[],
            review_required_fields=[],
            warnings=[],
            errors=[],
            block_id="generic_block",
            version="0.1.0",
        )


def test_build_block_result_rejects_invalid_rejected_task_candidates() -> None:
    with pytest.raises(
        ValueError,
        match=r"rejected_task_candidates\[\]\.rejection_reasons must be a non-empty array",
    ):
        build_block_result(
            status="success",
            decision="human_review",
            summary="bad rejected candidate",
            risk_level="low",
            needs_approval=True,
            mode="dry_run",
            actual_execution=False,
            actions=[],
            blocked_actions=[],
            needs_review_actions=[],
            task_candidates=[],
            rejected_task_candidates=[
                {
                    "candidate_id": "candidate_x",
                    "action_type": "collect_data",
                    "classification": "allow",
                    "impact_score": 60,
                    "risk_score": 20,
                    "confidence_score": 90,
                    "priority_score": 70,
                    "action": {"type": "collect_data", "target": "source_a"},
                    "rejection_reasons": [],
                }
            ],
            reason_codes=[],
            review_required_fields=[],
            warnings=[],
            errors=[],
            block_id="generic_block",
            version="0.1.0",
        )
