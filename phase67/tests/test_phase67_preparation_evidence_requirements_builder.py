from phase67.preparation_evidence_design.preparation_evidence_requirements_builder import (
    build_preparation_evidence_requirements,
)


def test_evidence_requirements_block_missing() -> None:
    data = build_preparation_evidence_requirements({"status": "PREPARATION_EVIDENCE_PACKAGE_READY"})
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert "phase66_go_no_go_report_reference" in data["required_evidence"]
    assert data["preparation_evidence_does_not_execute"] is True
