from __future__ import annotations

from typing import Any

from .safety_guard import GuardDecision


def _clamp_score(value: float) -> int:
    return max(0, min(100, int(round(value))))


def _impact_score(action_type: str, action: dict[str, Any]) -> int:
    base_map = {
        "collect_data": 55,
        "analyze": 65,
        "generate_report": 70,
        "notify_slack": 35,
    }
    base = base_map.get(action_type, 50)

    target = str(action.get("target", "")).strip()
    target_bonus = min(10, len(target) // 8)
    return _clamp_score(base + target_bonus)


def _classification_for_action(action: dict[str, Any], guard_decision: GuardDecision) -> str:
    if action in guard_decision.blocked_actions:
        return "block"
    if action in guard_decision.needs_review_actions:
        return "needs_review"
    return "allow"


def _risk_score(classification: str) -> int:
    return {
        "allow": 25,
        "needs_review": 55,
        "block": 85,
    }[classification]


def _confidence_score(classification: str) -> int:
    return {
        "allow": 85,
        "needs_review": 45,
        "block": 20,
    }[classification]


def _priority_score(*, impact: int, risk: int, confidence: int) -> int:
    return _clamp_score((impact * 0.45) + ((100 - risk) * 0.35) + (confidence * 0.20))


def score_task_candidates(
    requested_actions: list[dict[str, Any]],
    guard_decision: GuardDecision,
) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []

    for idx, action in enumerate(requested_actions):
        action_type = str(action.get("type", "")).strip()
        classification = _classification_for_action(action, guard_decision)

        impact = _impact_score(action_type, action)
        risk = _risk_score(classification)
        confidence = _confidence_score(classification)
        priority = _priority_score(impact=impact, risk=risk, confidence=confidence)

        scored.append(
            {
                "candidate_id": f"candidate_{idx + 1}",
                "action_type": action_type,
                "classification": classification,
                "impact_score": impact,
                "risk_score": risk,
                "confidence_score": confidence,
                "priority_score": priority,
                "action": action,
            }
        )

    scored.sort(
        key=lambda item: (
            -item["priority_score"],
            item["risk_score"],
            item["action_type"],
        )
    )
    return scored