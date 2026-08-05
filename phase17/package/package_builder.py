from __future__ import annotations


def _collect_reject_reasons(comparison_result: dict) -> list[str]:
    reasons: list[str] = []

    explicit_reasons = comparison_result.get("rejected_reasons", [])
    if isinstance(explicit_reasons, list):
        reasons.extend(str(reason) for reason in explicit_reasons)

    for item in comparison_result.get("candidates_report", []):
        policy = item.get("policy", {}) if isinstance(item, dict) else {}
        policy_reasons = policy.get("reasons", [])
        if policy.get("status") == "POLICY_VIOLATION" and isinstance(policy_reasons, list):
            reasons.extend(str(reason) for reason in policy_reasons)

    # Keep stable order while deduplicating.
    unique_reasons: list[str] = []
    for reason in reasons:
        if reason not in unique_reasons:
            unique_reasons.append(reason)
    return unique_reasons


def build_decision_package(comparison_result: dict) -> dict:
    selected_candidate_id = comparison_result.get("selected_candidate_id")
    if not selected_candidate_id:
        return {
            "phase": "17",
            "mode": "DRY_RUN",
            "human_approval_required": True,
            "selected_candidate_id": selected_candidate_id,
            "comparison_result": comparison_result,
            "status": "FAIL",
            "reason": "selected_candidate_id_missing",
        }

    return {
        "phase": "17",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "selected_candidate_id": selected_candidate_id,
        "risks": [
            "candidate_not_applied",
            "requires_manual_review_before_apply",
        ],
        "reject_reasons": _collect_reject_reasons(comparison_result),
        "approve_instructions": [
            "APPROVE allows only next dry-run stage",
            "REJECT stops the pipeline",
            "NEEDS_REVISION returns to candidate generation",
        ],
        "comparison_result": comparison_result,
        "status": "READY_FOR_HUMAN_REVIEW",
    }
