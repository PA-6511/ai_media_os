from __future__ import annotations

from phase16.candidates.candidate_model import Candidate


def generate_candidates(task_name: str, count: int = 3) -> list[Candidate]:
    """Return deterministic, safe dummy candidates for phase16 comparison."""
    _ = count  # Keep signature stable while phase16 always returns 3 candidates.
    return [
        Candidate(
            candidate_id="minimal",
            summary=f"{task_name}: minimal safe proposal",
            changed_files=["phase16/sandbox/minimal.txt"],
            diff_size=3,
            risk_level="LOW",
            has_deletion=False,
            touches_allowlist_only=True,
            expected_test_impact="small",
            notes=["smallest diff", "dry-run oriented"],
        ),
        Candidate(
            candidate_id="moderate",
            summary=f"{task_name}: moderate safe proposal",
            changed_files=["phase16/sandbox/moderate_a.txt", "phase16/sandbox/moderate_b.txt"],
            diff_size=9,
            risk_level="MEDIUM",
            has_deletion=False,
            touches_allowlist_only=True,
            expected_test_impact="medium",
            notes=["broader scope than minimal"],
        ),
        Candidate(
            candidate_id="risky",
            summary=f"{task_name}: risky proposal",
            changed_files=["core/unsafe_target.py"],
            diff_size=2,
            risk_level="HIGH",
            has_deletion=True,
            touches_allowlist_only=False,
            expected_test_impact="large",
            notes=["contains deletion", "touches outside allowlist"],
        ),
    ]
