from __future__ import annotations

from phase16.candidates.candidate_model import Candidate


_BLOCKED_RISKS = {"HIGH", "CRITICAL"}


def validate_candidate(candidate: Candidate) -> dict:
    reasons: list[str] = []

    if candidate.has_deletion:
        reasons.append("has_deletion=True is forbidden")

    if not candidate.touches_allowlist_only:
        reasons.append("touches_allowlist_only=False is forbidden")

    if candidate.risk_level.upper() in _BLOCKED_RISKS:
        reasons.append(f"risk_level={candidate.risk_level} is forbidden")

    status = "POLICY_VIOLATION" if reasons else "PASS"
    return {"status": status, "reasons": reasons}
