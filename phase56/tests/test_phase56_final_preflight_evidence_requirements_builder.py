from phase56.final_preflight_design.final_preflight_evidence_requirements_builder import (
    build_final_preflight_evidence_requirements,
)


def test_final_preflight_evidence_requirements_blocks_missing() -> None:
    data = build_final_preflight_evidence_requirements({"status": "FINAL_PREFLIGHT_PACKAGE_READY"})
    assert data["status"] == "FINAL_PREFLIGHT_EVIDENCE_REQUIREMENTS_READY"
    assert data["evidence_required"] is True
    assert data["missing_evidence_blocks_progress"] is True
    assert data["final_preflight_evidence_does_not_execute"] is True
    assert "dry_run_mode_confirmation" in data["required_evidence"]
