from phase23.execution_design.final_manual_gate_builder import build_final_manual_gate


def test_final_manual_gate_contains_non_execute_guard() -> None:
    gate = build_final_manual_gate({})
    assert gate["status"] == "FINAL_MANUAL_GATE_READY"
    assert gate["approve_does_not_execute"] is True
    assert "APPROVE_PHASE24_PLANNING_ONLY" in gate["allowed_decisions"]
