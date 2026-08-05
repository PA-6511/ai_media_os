from phase16.candidates.candidate_model import Candidate
from phase16.scoring.compare_candidates import compare_candidates


def test_minimal_safe_candidate_is_selected() -> None:
    candidates = [
        Candidate(
            candidate_id="safe_small",
            summary="safe_small",
            changed_files=["phase16/a"],
            diff_size=2,
            risk_level="LOW",
            has_deletion=False,
            touches_allowlist_only=True,
            expected_test_impact="small",
            notes=[],
        ),
        Candidate(
            candidate_id="safe_large",
            summary="safe_large",
            changed_files=["phase16/b"],
            diff_size=8,
            risk_level="LOW",
            has_deletion=False,
            touches_allowlist_only=True,
            expected_test_impact="small",
            notes=[],
        ),
        Candidate(
            candidate_id="unsafe",
            summary="unsafe",
            changed_files=["core/c"],
            diff_size=1,
            risk_level="HIGH",
            has_deletion=True,
            touches_allowlist_only=False,
            expected_test_impact="small",
            notes=[],
        ),
    ]

    result = compare_candidates(candidates)

    assert result["pipeline_status"] == "PASS_DRY_RUN_ONLY"
    assert result["selected_candidate_id"] == "safe_small"


def test_compare_fails_when_no_selectable_candidates() -> None:
    candidates = [
        Candidate(
            candidate_id="unsafe1",
            summary="unsafe1",
            changed_files=["core/x"],
            diff_size=1,
            risk_level="HIGH",
            has_deletion=True,
            touches_allowlist_only=False,
            expected_test_impact="large",
            notes=[],
        ),
        Candidate(
            candidate_id="unsafe2",
            summary="unsafe2",
            changed_files=["core/y"],
            diff_size=2,
            risk_level="CRITICAL",
            has_deletion=False,
            touches_allowlist_only=False,
            expected_test_impact="large",
            notes=[],
        ),
    ]

    result = compare_candidates(candidates)

    assert result["pipeline_status"] == "FAIL"
    assert result["selected_candidate_id"] is None
