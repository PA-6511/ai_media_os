from phase16.candidates.candidate_model import Candidate
from phase16.policy.candidate_policy import validate_candidate


def _base_candidate() -> Candidate:
    return Candidate(
        candidate_id="base",
        summary="base",
        changed_files=["phase16/x.txt"],
        diff_size=3,
        risk_level="LOW",
        has_deletion=False,
        touches_allowlist_only=True,
        expected_test_impact="small",
        notes=[],
    )


def test_has_deletion_is_policy_violation() -> None:
    candidate = _base_candidate()
    candidate.has_deletion = True
    result = validate_candidate(candidate)
    assert result["status"] == "POLICY_VIOLATION"


def test_outside_allowlist_is_policy_violation() -> None:
    candidate = _base_candidate()
    candidate.touches_allowlist_only = False
    result = validate_candidate(candidate)
    assert result["status"] == "POLICY_VIOLATION"


def test_high_and_critical_risk_are_policy_violation() -> None:
    candidate_h = _base_candidate()
    candidate_h.risk_level = "HIGH"
    result_h = validate_candidate(candidate_h)
    assert result_h["status"] == "POLICY_VIOLATION"

    candidate_c = _base_candidate()
    candidate_c.risk_level = "CRITICAL"
    result_c = validate_candidate(candidate_c)
    assert result_c["status"] == "POLICY_VIOLATION"
