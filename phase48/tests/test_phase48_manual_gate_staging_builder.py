from phase48.staging_design.manual_gate_staging_builder import build_manual_gate_staging


def test_manual_gate_staging_allows_phase49_planning_only() -> None:
    gate = build_manual_gate_staging({"status": "STAGING_PACKAGE_READY"})
    assert gate["status"] == "MANUAL_GATE_STAGING_READY"
    assert gate["staging_gate_does_not_execute"] is True
    assert "ALLOW_PHASE49_PLANNING_ONLY" in gate["allowed_decisions"]
