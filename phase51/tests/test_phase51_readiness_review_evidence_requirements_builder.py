from phase51.readiness_review_design.readiness_review_evidence_requirements_builder import (
    build_readiness_review_evidence_requirements,
)


def test_readiness_review_evidence_requirements_blocks_missing() -> None:
    data = build_readiness_review_evidence_requirements({"status": "READINESS_REVIEW_PACKAGE_READY"})
    assert data["status"] == "READINESS_REVIEW_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["readiness_review_evidence_does_not_execute"] is True
    assert "dry_run_mode_confirmation" in data["required_evidence"]
