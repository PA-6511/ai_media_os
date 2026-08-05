from phase36.launch_design.launch_evidence_requirements_builder import (
    build_launch_evidence_requirements,
)


def test_launch_evidence_requirements_blocks_progress_on_missing() -> None:
    data = build_launch_evidence_requirements(
        {"status": "MANUAL_DRY_RUN_EXECUTION_LAUNCH_PACKAGE_READY"}
    )
    assert data["status"] == "LAUNCH_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["launch_evidence_does_not_execute"] is True
