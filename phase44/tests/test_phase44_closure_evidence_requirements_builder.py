from phase44.closure_design.closure_evidence_requirements_builder import (
    build_closure_evidence_requirements,
)


def test_closure_evidence_requirements_blocks_missing() -> None:
    data = build_closure_evidence_requirements({"status": "CLOSURE_PACKAGE_READY"})
    assert data["status"] == "CLOSURE_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["closure_evidence_does_not_execute"] is True
    assert "dry_run_mode_confirmation" in data["required_evidence"]
