from phase53.final_go_review_design.final_go_review_evidence_requirements_builder import (
    build_final_go_review_evidence_requirements,
)


def test_final_go_review_evidence_requirements_blocks_missing() -> None:
    data = build_final_go_review_evidence_requirements({"status": "FINAL_GO_REVIEW_PACKAGE_READY"})
    assert data["status"] == "FINAL_GO_REVIEW_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["final_go_review_evidence_does_not_execute"] is True
    assert "dry_run_mode_confirmation" in data["required_evidence"]
