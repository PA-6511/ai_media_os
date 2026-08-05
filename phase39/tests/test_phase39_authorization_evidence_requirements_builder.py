from phase39.authorization_design.authorization_evidence_requirements_builder import (
    build_authorization_evidence_requirements,
)


def test_authorization_evidence_requirements_blocks_progress_on_missing() -> None:
    data = build_authorization_evidence_requirements(
        {"status": "MANUAL_DRY_RUN_EXECUTION_AUTHORIZATION_PACKAGE_READY"}
    )
    assert data["status"] == "AUTHORIZATION_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["authorization_evidence_does_not_execute"] is True
