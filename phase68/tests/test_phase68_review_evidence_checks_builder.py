from phase68.preparation_review_design.review_evidence_checks_builder import (
    build_review_evidence_checks,
)


def test_review_evidence_checks_block_missing() -> None:
    data = build_review_evidence_checks({"status": "PREPARATION_REVIEW_PACKAGE_READY"})
    assert data["evidence_checks_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert "phase67_report_reference" in data["required_checks"]
    assert data["review_evidence_checks_does_not_execute"] is True
