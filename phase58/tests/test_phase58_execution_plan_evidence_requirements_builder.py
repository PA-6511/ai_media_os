from phase58.execution_plan_design.execution_plan_evidence_requirements_builder import (
    build_execution_plan_evidence_requirements,
)


def test_execution_plan_evidence_requirements_blocks_missing() -> None:
    data = build_execution_plan_evidence_requirements({"status": "EXECUTION_PLAN_PACKAGE_READY"})
    assert data["status"] == "EXECUTION_PLAN_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["execution_plan_evidence_does_not_execute"] is True
    assert "dry_run_mode_confirmation" in data["required_evidence"]
