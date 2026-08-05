from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class Candidate:
    candidate_id: str
    summary: str
    changed_files: list[str]
    diff_size: int
    risk_level: str
    has_deletion: bool
    touches_allowlist_only: bool
    expected_test_impact: str
    notes: list[str]

    def to_dict(self) -> dict:
        return asdict(self)
