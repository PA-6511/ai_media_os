from __future__ import annotations

from typing import Any


DEFAULT_QUALITY_METRICS_POLICY: dict[str, Any] = {
    "quality_score_base": 55,
    "priority_weight": 0.35,
    "accepted_risk_weight": 0.2,
    "rejection_penalty_weight": 30,
    "validation_penalty_fail": 35,
    "validation_penalty_warn": 15,
    "risk_gap_weight": 0.7,
    "risk_rejection_penalty_weight": 20,
    "readiness_min_quality_score": 60,
    "readiness_min_risk_balance": 50,
    "readiness_allowed_validation_results": ["PASS"],
}


def _clamp_0_100(value: int) -> int:
    if value < 0:
        return 0
    if value > 100:
        return 100
    return value


def _avg(items: list[int]) -> int:
    if not items:
        return 0
    return int(round(sum(items) / len(items)))


def _to_float(value: Any, fallback: float) -> float:
    if isinstance(value, bool):
        return fallback
    if isinstance(value, (int, float)):
        return float(value)
    return fallback


def _to_int(value: Any, fallback: int) -> int:
    if isinstance(value, bool):
        return fallback
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(round(value))
    return fallback


def _build_quality_policy(override: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(override, dict):
        return dict(DEFAULT_QUALITY_METRICS_POLICY)

    policy = dict(DEFAULT_QUALITY_METRICS_POLICY)
    policy.update(override)

    return {
        "quality_score_base": _to_int(
            policy.get("quality_score_base"),
            DEFAULT_QUALITY_METRICS_POLICY["quality_score_base"],
        ),
        "priority_weight": _to_float(
            policy.get("priority_weight"),
            DEFAULT_QUALITY_METRICS_POLICY["priority_weight"],
        ),
        "accepted_risk_weight": _to_float(
            policy.get("accepted_risk_weight"),
            DEFAULT_QUALITY_METRICS_POLICY["accepted_risk_weight"],
        ),
        "rejection_penalty_weight": _to_float(
            policy.get("rejection_penalty_weight"),
            DEFAULT_QUALITY_METRICS_POLICY["rejection_penalty_weight"],
        ),
        "validation_penalty_fail": _to_int(
            policy.get("validation_penalty_fail"),
            DEFAULT_QUALITY_METRICS_POLICY["validation_penalty_fail"],
        ),
        "validation_penalty_warn": _to_int(
            policy.get("validation_penalty_warn"),
            DEFAULT_QUALITY_METRICS_POLICY["validation_penalty_warn"],
        ),
        "risk_gap_weight": _to_float(
            policy.get("risk_gap_weight"),
            DEFAULT_QUALITY_METRICS_POLICY["risk_gap_weight"],
        ),
        "risk_rejection_penalty_weight": _to_float(
            policy.get("risk_rejection_penalty_weight"),
            DEFAULT_QUALITY_METRICS_POLICY["risk_rejection_penalty_weight"],
        ),
        "readiness_min_quality_score": _to_int(
            policy.get("readiness_min_quality_score"),
            DEFAULT_QUALITY_METRICS_POLICY["readiness_min_quality_score"],
        ),
        "readiness_min_risk_balance": _to_int(
            policy.get("readiness_min_risk_balance"),
            DEFAULT_QUALITY_METRICS_POLICY["readiness_min_risk_balance"],
        ),
        "readiness_allowed_validation_results": [
            str(item) for item in policy.get("readiness_allowed_validation_results", ["PASS"])
        ],
    }


def compute_quality_metrics(
    block_result: dict[str, Any],
    *,
    proposal_validation_result: str = "NOT_RUN",
    proposal_failed_checks: list[str] | None = None,
    proposal_warnings: list[str] | None = None,
    policy_quality_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    quality_policy = _build_quality_policy(policy_quality_metrics)

    task_candidates = list(block_result.get("task_candidates", []))
    rejected_task_candidates = list(block_result.get("rejected_task_candidates", []))

    accepted_priority_scores = [int(item.get("priority_score", 0)) for item in task_candidates]
    accepted_risk_scores = [int(item.get("risk_score", 0)) for item in task_candidates]
    rejected_risk_scores = [int(item.get("risk_score", 0)) for item in rejected_task_candidates]

    avg_priority = _avg(accepted_priority_scores)
    avg_accepted_risk = _avg(accepted_risk_scores)
    avg_rejected_risk = _avg(rejected_risk_scores)

    rejected_count = len(rejected_task_candidates)
    accepted_count = len(task_candidates)
    total_count = accepted_count + rejected_count
    rejection_ratio = (rejected_count / total_count) if total_count else 0.0

    failed_checks = list(proposal_failed_checks or [])
    warnings = list(proposal_warnings or [])

    rejection_penalty = int(round(rejection_ratio * quality_policy["rejection_penalty_weight"]))
    validation_penalty = 0
    if proposal_validation_result == "FAIL":
        validation_penalty = quality_policy["validation_penalty_fail"]
    elif proposal_validation_result == "WARN":
        validation_penalty = quality_policy["validation_penalty_warn"]

    quality_score = _clamp_0_100(
        quality_policy["quality_score_base"]
        + int(round(avg_priority * quality_policy["priority_weight"]))
        - int(round(avg_accepted_risk * quality_policy["accepted_risk_weight"]))
        - rejection_penalty
        - validation_penalty
    )

    risk_balance = _clamp_0_100(
        100
        - int(round(abs(avg_rejected_risk - avg_accepted_risk) * quality_policy["risk_gap_weight"]))
        - int(round(rejection_ratio * quality_policy["risk_rejection_penalty_weight"]))
    )

    review_readiness = "not_ready"
    allowed_validation_results = set(quality_policy["readiness_allowed_validation_results"])
    if (
        proposal_validation_result in allowed_validation_results
        and quality_score >= quality_policy["readiness_min_quality_score"]
        and risk_balance >= quality_policy["readiness_min_risk_balance"]
    ):
        review_readiness = "ready"
    elif proposal_validation_result in {"PASS", "WARN", "NOT_RUN"}:
        review_readiness = "needs_attention"

    return {
        "quality_score": quality_score,
        "risk_balance": risk_balance,
        "review_readiness": review_readiness,
        "details": {
            "accepted_candidates": accepted_count,
            "rejected_candidates": rejected_count,
            "avg_priority_score": avg_priority,
            "avg_accepted_risk_score": avg_accepted_risk,
            "avg_rejected_risk_score": avg_rejected_risk,
            "proposal_validation_result": proposal_validation_result,
            "proposal_failed_checks_count": len(failed_checks),
            "proposal_warnings_count": len(warnings),
            "policy": quality_policy,
        },
    }