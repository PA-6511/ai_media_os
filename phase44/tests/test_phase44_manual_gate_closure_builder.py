from phase44.closure_design.manual_gate_closure_builder import build_manual_gate_closure


def test_manual_gate_closure_allows_phase45_planning_only() -> None:
    gate = build_manual_gate_closure({"status": "CLOSURE_PACKAGE_READY"})
    assert gate["status"] == "MANUAL_GATE_CLOSURE_READY"
    assert gate["closure_gate_does_not_execute"] is True
    assert "ALLOW_PHASE45_PLANNING_ONLY" in gate["allowed_decisions"]
