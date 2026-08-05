from phase45.handoff_design.manual_gate_handoff_builder import build_manual_gate_handoff


def test_manual_gate_handoff_allows_phase46_planning_only() -> None:
    gate = build_manual_gate_handoff({"status": "HANDOFF_PACKAGE_READY"})
    assert gate["status"] == "MANUAL_GATE_HANDOFF_READY"
    assert gate["handoff_gate_does_not_execute"] is True
    assert "ALLOW_PHASE46_PLANNING_ONLY" in gate["allowed_decisions"]
