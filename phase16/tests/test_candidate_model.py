from phase16.candidates.candidate_generator import generate_candidates
from phase16.candidates.candidate_model import Candidate


def test_candidate_to_dict_contains_required_fields() -> None:
    candidate = Candidate(
        candidate_id="c1",
        summary="summary",
        changed_files=["phase16/a.py"],
        diff_size=1,
        risk_level="LOW",
        has_deletion=False,
        touches_allowlist_only=True,
        expected_test_impact="small",
        notes=["note"],
    )

    data = candidate.to_dict()
    required = {
        "candidate_id",
        "summary",
        "changed_files",
        "diff_size",
        "risk_level",
        "has_deletion",
        "touches_allowlist_only",
        "expected_test_impact",
        "notes",
    }
    assert required.issubset(set(data.keys()))


def test_generate_candidates_returns_three() -> None:
    candidates = generate_candidates("task")
    assert len(candidates) == 3
