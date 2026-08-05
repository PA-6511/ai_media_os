from phase40.validation_design.validation_evidence_requirements_builder import (
    build_validation_evidence_requirements,
)


def test_validation_evidence_requirements_blocks_progress_on_missing() -> None:
    data = build_validation_evidence_requirements(
        {"status": "MANUAL_DRY_RUN_EXECUTION_VALIDATION_PACKAGE_READY"}
    )
    assert data["status"] == "VALIDATION_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["validation_evidence_does_not_execute"] is True
