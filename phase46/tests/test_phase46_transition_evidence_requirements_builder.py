from phase46.transition_design.transition_evidence_requirements_builder import (
    build_transition_evidence_requirements,
)


def test_transition_evidence_requirements_blocks_missing() -> None:
    data = build_transition_evidence_requirements({"status": "TRANSITION_PACKAGE_READY"})
    assert data["status"] == "TRANSITION_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["transition_evidence_does_not_execute"] is True
    assert "dry_run_mode_confirmation" in data["required_evidence"]
