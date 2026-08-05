from phase47.integration_design.integration_evidence_requirements_builder import (
    build_integration_evidence_requirements,
)


def test_integration_evidence_requirements_blocks_missing() -> None:
    data = build_integration_evidence_requirements({"status": "INTEGRATION_PACKAGE_READY"})
    assert data["status"] == "INTEGRATION_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["integration_evidence_does_not_execute"] is True
    assert "dry_run_mode_confirmation" in data["required_evidence"]
