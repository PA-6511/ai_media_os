from phase60.runbook_design.runbook_evidence_requirements_builder import (
    build_runbook_evidence_requirements,
)


def test_runbook_evidence_requirements_blocks_missing() -> None:
    data = build_runbook_evidence_requirements({"status": "RUNBOOK_PACKAGE_READY"})
    assert data["status"] == "RUNBOOK_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["runbook_evidence_does_not_execute"] is True
    assert "dry_run_mode_confirmation" in data["required_evidence"]
