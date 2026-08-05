from __future__ import annotations


def judge_promotion_readiness(
    quality_result: dict,
    safety_result: dict,
    rollback_result: dict,
) -> dict:
    reasons: list[str] = []

    if quality_result.get("quality_status") != "PASS":
        reasons.append(f"quality_status={quality_result.get('quality_status')}")

    if safety_result.get("safety_status") != "PASS":
        reasons.append(f"safety_status={safety_result.get('safety_status')}")

    if rollback_result.get("rollback_status") != "PASS":
        reasons.append(f"rollback_status={rollback_result.get('rollback_status')}")

    if not reasons:
        return {
            "promotion_status": "READY_FOR_PHASE20_DESIGN",
            "can_promote": False,
            "next_step": "prepare_phase20_design_review",
            "reasons": [],
        }

    return {
        "promotion_status": "NOT_READY",
        "can_promote": False,
        "next_step": "fix_phase18_or_review_findings",
        "reasons": reasons,
    }
