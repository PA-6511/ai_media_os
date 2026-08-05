from phase37.trigger_design.trigger_evidence_requirements_builder import (
    build_trigger_evidence_requirements,
)


def test_trigger_evidence_requirements_blocks_progress_on_missing() -> None:
    data = build_trigger_evidence_requirements(
        {"status": "MANUAL_DRY_RUN_EXECUTION_TRIGGER_PACKAGE_READY"}
    )
    assert data["status"] == "TRIGGER_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["trigger_evidence_does_not_execute"] is True
