from phase49.release_planning_design.release_planning_evidence_requirements_builder import (
    build_release_planning_evidence_requirements,
)


def test_release_planning_evidence_requirements_blocks_missing() -> None:
    data = build_release_planning_evidence_requirements({"status": "RELEASE_PLANNING_PACKAGE_READY"})
    assert data["status"] == "RELEASE_PLANNING_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["release_planning_evidence_does_not_execute"] is True
    assert "dry_run_mode_confirmation" in data["required_evidence"]
