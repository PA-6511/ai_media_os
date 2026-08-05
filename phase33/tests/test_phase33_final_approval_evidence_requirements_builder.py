from phase33.approval_design.final_approval_evidence_requirements_builder import (
    build_final_approval_evidence_requirements,
)


def test_final_approval_evidence_requirements_blocks_progress_on_missing() -> None:
    data = build_final_approval_evidence_requirements(
        {"status": "MANUAL_DRY_RUN_EXECUTION_APPROVAL_PACKAGE_READY"}
    )
    assert data["status"] == "FINAL_APPROVAL_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["final_approval_evidence_does_not_execute"] is True
