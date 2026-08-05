from phase43.completion_design.completion_evidence_requirements_builder import (
    build_completion_evidence_requirements,
)


def test_completion_evidence_requirements_blocks_missing() -> None:
    data = build_completion_evidence_requirements({"status": "COMPLETION_PACKAGE_READY"})
    assert data["status"] == "COMPLETION_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["evidence_does_not_execute"] is True
    assert "dry_run_mode_confirmation" in data["required_evidence"]
