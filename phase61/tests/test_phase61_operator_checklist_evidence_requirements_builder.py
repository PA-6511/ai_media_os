from phase61.operator_checklist_design.operator_checklist_evidence_requirements_builder import (
    build_operator_checklist_evidence_requirements,
)


def test_operator_checklist_evidence_requirements_blocks_missing() -> None:
    data = build_operator_checklist_evidence_requirements({"status": "OPERATOR_CHECKLIST_PACKAGE_READY"})
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert "manual_approval_reference" in data["required_evidence"]
    assert data["operator_checklist_evidence_does_not_execute"] is True
