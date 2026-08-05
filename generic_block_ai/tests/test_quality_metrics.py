from generic_block_ai.app.quality_metrics import compute_quality_metrics


def test_compute_quality_metrics_ready_when_balanced_and_validated() -> None:
    block_result = {
        "task_candidates": [
            {
                "priority_score": 78,
                "risk_score": 35,
            },
            {
                "priority_score": 70,
                "risk_score": 30,
            },
        ],
        "rejected_task_candidates": [
            {
                "priority_score": 20,
                "risk_score": 80,
            }
        ],
    }

    metrics = compute_quality_metrics(
        block_result,
        proposal_validation_result="PASS",
        proposal_failed_checks=[],
        proposal_warnings=[],
    )

    assert 0 <= metrics["quality_score"] <= 100
    assert 0 <= metrics["risk_balance"] <= 100
    assert metrics["review_readiness"] in {"ready", "needs_attention", "not_ready"}
    assert metrics["review_readiness"] == "ready"


def test_compute_quality_metrics_not_ready_when_validation_fails() -> None:
    block_result = {
        "task_candidates": [
            {
                "priority_score": 82,
                "risk_score": 40,
            }
        ],
        "rejected_task_candidates": [],
    }

    metrics = compute_quality_metrics(
        block_result,
        proposal_validation_result="FAIL",
        proposal_failed_checks=["proposal.mode must be dry_run"],
        proposal_warnings=[],
    )

    assert metrics["review_readiness"] == "not_ready"
    assert metrics["details"]["proposal_failed_checks_count"] == 1


def test_compute_quality_metrics_respects_policy_threshold_override() -> None:
    block_result = {
        "task_candidates": [
            {
                "priority_score": 78,
                "risk_score": 35,
            },
            {
                "priority_score": 70,
                "risk_score": 30,
            },
        ],
        "rejected_task_candidates": [
            {
                "priority_score": 20,
                "risk_score": 80,
            }
        ],
    }

    metrics = compute_quality_metrics(
        block_result,
        proposal_validation_result="PASS",
        proposal_failed_checks=[],
        proposal_warnings=[],
        policy_quality_metrics={
            "readiness_min_quality_score": 90,
            "readiness_min_risk_balance": 90,
            "readiness_allowed_validation_results": ["PASS"],
        },
    )

    assert metrics["review_readiness"] == "needs_attention"
    assert metrics["details"]["policy"]["readiness_min_quality_score"] == 90
    assert metrics["details"]["policy"]["readiness_min_risk_balance"] == 90