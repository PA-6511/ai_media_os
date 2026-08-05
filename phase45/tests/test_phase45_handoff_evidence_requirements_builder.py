from phase45.handoff_design.handoff_evidence_requirements_builder import (
    build_handoff_evidence_requirements,
)


def test_handoff_evidence_requirements_blocks_missing() -> None:
    data = build_handoff_evidence_requirements({"status": "HANDOFF_PACKAGE_READY"})
    assert data["status"] == "HANDOFF_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["handoff_evidence_does_not_execute"] is True
    assert "dry_run_mode_confirmation" in data["required_evidence"]
