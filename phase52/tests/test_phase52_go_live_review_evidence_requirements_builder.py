from phase52.go_live_review_design.go_live_review_evidence_requirements_builder import (
    build_go_live_review_evidence_requirements,
)


def test_go_live_review_evidence_requirements_blocks_missing() -> None:
    data = build_go_live_review_evidence_requirements({"status": "GO_LIVE_REVIEW_PACKAGE_READY"})
    assert data["status"] == "GO_LIVE_REVIEW_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["go_live_review_evidence_does_not_execute"] is True
    assert "dry_run_mode_confirmation" in data["required_evidence"]
