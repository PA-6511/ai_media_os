from phase48.staging_design.staging_evidence_requirements_builder import (
    build_staging_evidence_requirements,
)


def test_staging_evidence_requirements_blocks_missing() -> None:
    data = build_staging_evidence_requirements({"status": "STAGING_PACKAGE_READY"})
    assert data["status"] == "STAGING_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["staging_evidence_does_not_execute"] is True
    assert "dry_run_mode_confirmation" in data["required_evidence"]
