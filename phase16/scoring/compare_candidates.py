from __future__ import annotations

from phase16.candidates.candidate_model import Candidate
from phase16.policy.candidate_policy import validate_candidate
from phase16.scoring.score_candidate import score_candidate


def compare_candidates(candidates: list[Candidate]) -> dict:
    candidates_report: list[dict] = []

    for candidate in candidates:
        policy_result = validate_candidate(candidate)
        score_result = score_candidate(candidate, policy_result)
        candidates_report.append(
            {
                "candidate": candidate.to_dict(),
                "policy": policy_result,
                "score": score_result,
            }
        )

    selectable = [
        item for item in candidates_report if item["score"].get("selectable", False)
    ]

    if not selectable:
        return {
            "selected_candidate_id": None,
            "candidates_report": candidates_report,
            "pipeline_status": "FAIL",
        }

    selected = max(
        selectable,
        key=lambda item: (
            item["score"]["score"],
            -item["candidate"]["diff_size"],
        ),
    )

    return {
        "selected_candidate_id": selected["candidate"]["candidate_id"],
        "candidates_report": candidates_report,
        "pipeline_status": "PASS_DRY_RUN_ONLY",
    }
