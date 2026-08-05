from phase59.operation_plan_design.operation_plan_evidence_requirements_builder import (
    build_operation_plan_evidence_requirements,
)


def test_operation_plan_evidence_requirements_blocks_missing() -> None:
    data = build_operation_plan_evidence_requirements({"status": "OPERATION_PLAN_PACKAGE_READY"})
    assert data["status"] == "OPERATION_PLAN_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["operation_plan_evidence_does_not_execute"] is True
    assert "dry_run_mode_confirmation" in data["required_evidence"]
