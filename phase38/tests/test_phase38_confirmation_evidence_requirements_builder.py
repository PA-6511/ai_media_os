from phase38.confirmation_design.confirmation_evidence_requirements_builder import (
    build_confirmation_evidence_requirements,
)


def test_confirmation_evidence_requirements_blocks_progress_on_missing() -> None:
    data = build_confirmation_evidence_requirements(
        {"status": "MANUAL_DRY_RUN_EXECUTION_CONFIRMATION_PACKAGE_READY"}
    )
    assert data["status"] == "CONFIRMATION_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["confirmation_evidence_does_not_execute"] is True
