from phase16.candidates.candidate_model import Candidate
from phase16.policy.candidate_policy import validate_candidate
from phase16.scoring.score_candidate import score_candidate


def test_policy_violation_candidate_is_not_selectable() -> None:
    candidate = Candidate(
        candidate_id="bad",
        summary="bad",
        changed_files=["core/x.py"],
        diff_size=1,
        risk_level="HIGH",
        has_deletion=True,
        touches_allowlist_only=False,
        expected_test_impact="small",
        notes=[],
    )

    policy = validate_candidate(candidate)
    scored = score_candidate(candidate, policy)

    assert policy["status"] == "POLICY_VIOLATION"
    assert scored["selectable"] is False
