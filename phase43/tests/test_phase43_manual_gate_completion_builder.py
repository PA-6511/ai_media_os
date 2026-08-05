from phase43.completion_design.manual_gate_completion_builder import build_manual_gate_completion


def test_manual_gate_completion_allows_phase44_planning_only() -> None:
    gate = build_manual_gate_completion({"status": "COMPLETION_PACKAGE_READY"})
    assert gate["status"] == "MANUAL_GATE_COMPLETION_READY"
    assert gate["allow_does_not_execute"] is True
    assert "ALLOW_PHASE44_PLANNING_ONLY" in gate["allowed_decisions"]
