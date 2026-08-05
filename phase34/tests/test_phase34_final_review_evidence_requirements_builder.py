from phase34.final_review_design.final_review_evidence_requirements_builder import (
    build_final_review_evidence_requirements,
)


def test_final_review_evidence_requirements_blocks_progress_on_missing() -> None:
    data = build_final_review_evidence_requirements(
        {"status": "FINAL_PRE_EXECUTION_REVIEW_READY"}
    )
    assert data["status"] == "FINAL_REVIEW_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["final_review_evidence_does_not_execute"] is True
