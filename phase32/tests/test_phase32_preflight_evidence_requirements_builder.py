from phase32.preflight_design.preflight_evidence_requirements_builder import (
    build_preflight_evidence_requirements,
)


def test_preflight_evidence_requirements_blocks_progress_on_missing() -> None:
    data = build_preflight_evidence_requirements(
        {"status": "MANUAL_DRY_RUN_PREFLIGHT_PACKAGE_READY"}
    )
    assert data["status"] == "PREFLIGHT_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["preflight_evidence_does_not_execute"] is True
