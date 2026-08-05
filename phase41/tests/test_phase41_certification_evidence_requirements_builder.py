from phase41.certification_design.certification_evidence_requirements_builder import (
    build_certification_evidence_requirements,
)


def test_certification_evidence_requirements_blocks_progress_on_missing() -> None:
    data = build_certification_evidence_requirements(
        {"status": "MANUAL_DRY_RUN_EXECUTION_CERTIFICATION_PACKAGE_READY"}
    )
    assert data["status"] == "CERTIFICATION_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["certification_evidence_does_not_execute"] is True
