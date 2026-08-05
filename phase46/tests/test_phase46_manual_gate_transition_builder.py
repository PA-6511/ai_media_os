from phase46.transition_design.manual_gate_transition_builder import build_manual_gate_transition


def test_manual_gate_transition_allows_phase47_planning_only() -> None:
    gate = build_manual_gate_transition({"status": "TRANSITION_PACKAGE_READY"})
    assert gate["status"] == "MANUAL_GATE_TRANSITION_READY"
    assert gate["transition_gate_does_not_execute"] is True
    assert "ALLOW_PHASE47_PLANNING_ONLY" in gate["allowed_decisions"]
