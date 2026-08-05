from phase31.control_design.evidence_requirements_builder import (
    build_evidence_requirements,
)


def test_evidence_requirements_blocks_without_evidence() -> None:
    data = build_evidence_requirements(
        {"status": "PRE_EXECUTION_CONTROL_DESIGN_READY"}
    )
    assert data["status"] == "EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["evidence_does_not_execute"] is True
