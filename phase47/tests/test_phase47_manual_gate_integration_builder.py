from phase47.integration_design.manual_gate_integration_builder import build_manual_gate_integration


def test_manual_gate_integration_allows_phase48_planning_only() -> None:
    gate = build_manual_gate_integration({"status": "INTEGRATION_PACKAGE_READY"})
    assert gate["status"] == "MANUAL_GATE_INTEGRATION_READY"
    assert gate["integration_gate_does_not_execute"] is True
    assert "ALLOW_PHASE48_PLANNING_ONLY" in gate["allowed_decisions"]
