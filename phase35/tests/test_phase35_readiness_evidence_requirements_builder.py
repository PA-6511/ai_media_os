from phase35.readiness_design.readiness_evidence_requirements_builder import (
    build_readiness_evidence_requirements,
)


def test_readiness_evidence_requirements_blocks_progress_on_missing() -> None:
    data = build_readiness_evidence_requirements(
        {"status": "MANUAL_DRY_RUN_EXECUTION_READINESS_PACKAGE_READY"}
    )
    assert data["status"] == "READINESS_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["readiness_evidence_does_not_execute"] is True
