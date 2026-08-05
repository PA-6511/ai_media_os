from __future__ import annotations

from phase16.candidates.candidate_model import Candidate

_RISK_SCORE = {
    "LOW": 30,
    "MEDIUM": 15,
    "HIGH": 0,
    "CRITICAL": -10,
}

_IMPACT_SCORE = {
    "small": 30,
    "medium": 15,
    "large": 0,
}


def score_candidate(candidate: Candidate, policy_result: dict) -> dict:
    reasons: list[str] = []

    if policy_result.get("status") == "POLICY_VIOLATION":
        reasons.extend(policy_result.get("reasons", []))
        return {
            "score": 0,
            "selectable": False,
            "reasons": reasons,
        }

    diff_component = max(0, 40 - candidate.diff_size)
    risk_component = _RISK_SCORE.get(candidate.risk_level.upper(), 0)
    impact_component = _IMPACT_SCORE.get(candidate.expected_test_impact.lower(), 0)

    score = diff_component + risk_component + impact_component
    reasons.append(f"diff_component={diff_component}")
    reasons.append(f"risk_component={risk_component}")
    reasons.append(f"impact_component={impact_component}")

    return {
        "score": score,
        "selectable": True,
        "reasons": reasons,
    }
