from __future__ import annotations

from typing import Any


DEFAULT_REVIEW_DECISION_POLICY: dict[str, Any] = {
    "block_on_status": ["error", "blocked"],
    "reject_on_validation_results": ["FAIL"],
    "reject_on_readiness": ["not_ready"],
    "approve_on_readiness": ["ready"],
}


def _normalize_policy(policy_override: dict[str, Any] | None) -> dict[str, list[str]]:
    if not isinstance(policy_override, dict):
        source = DEFAULT_REVIEW_DECISION_POLICY
    else:
        source = {**DEFAULT_REVIEW_DECISION_POLICY, **policy_override}

    return {
        "block_on_status": [str(item) for item in source.get("block_on_status", [])],
        "reject_on_validation_results": [
            str(item) for item in source.get("reject_on_validation_results", [])
        ],
        "reject_on_readiness": [str(item) for item in source.get("reject_on_readiness", [])],
        "approve_on_readiness": [str(item) for item in source.get("approve_on_readiness", [])],
    }


def build_recommended_decision(
    block_result: dict[str, Any],
    quality_metrics: dict[str, Any],
    *,
    policy_review_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = _normalize_policy(policy_review_decision)

    status = str(block_result.get("status", ""))
    review_readiness = str(quality_metrics.get("review_readiness", "needs_attention"))
    proposal_validation_result = str(
        quality_metrics.get("details", {}).get("proposal_validation_result", "NOT_RUN")
    )

    decision = "REQUIRE_HUMAN_REVIEW"
    reason = "requires_human_judgement"

    if status in set(policy["block_on_status"]):
        decision = "BLOCKED_BY_POLICY"
        reason = f"status={status}"
    elif proposal_validation_result in set(policy["reject_on_validation_results"]):
        decision = "RECOMMEND_REJECT"
        reason = f"validation={proposal_validation_result}"
    elif review_readiness in set(policy["reject_on_readiness"]):
        decision = "RECOMMEND_REJECT"
        reason = f"review_readiness={review_readiness}"
    elif review_readiness in set(policy["approve_on_readiness"]):
        decision = "RECOMMEND_APPROVE_DRY_RUN_ONLY"
        reason = f"review_readiness={review_readiness}"

    return {
        "recommended_decision": decision,
        "reason": reason,
        "policy_version": "review_decision_policy_v1",
        "safeguards": {
            "actual_auto_approve": False,
            "actual_auto_execute": False,
            "external_write_executed": False,
            "production_release": False,
            "requires_human_signoff": True,
        },
        "inputs": {
            "status": status,
            "review_readiness": review_readiness,
            "proposal_validation_result": proposal_validation_result,
        },
        "policy": policy,
    }