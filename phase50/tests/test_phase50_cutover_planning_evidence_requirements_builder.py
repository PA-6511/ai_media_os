from phase50.cutover_planning_design.cutover_planning_evidence_requirements_builder import (
    build_cutover_planning_evidence_requirements,
)


def test_cutover_planning_evidence_requirements_blocks_missing() -> None:
    data = build_cutover_planning_evidence_requirements({"status": "CUTOVER_PLANNING_PACKAGE_READY"})
    assert data["status"] == "CUTOVER_PLANNING_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["cutover_planning_evidence_does_not_execute"] is True
    assert "dry_run_mode_confirmation" in data["required_evidence"]
