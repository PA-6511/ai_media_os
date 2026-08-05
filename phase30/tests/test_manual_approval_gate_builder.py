from phase30.execution_design.manual_approval_gate_builder import build_manual_approval_gate


def test_manual_approval_gate_has_non_execute_guard() -> None:
    gate = build_manual_approval_gate({"status": "LIMITED_DRY_RUN_DESIGN_READY"})
    assert gate["status"] == "MANUAL_APPROVAL_GATE_READY"
    assert gate["allow_does_not_execute"] is True
    assert "ALLOW_PHASE31_PLANNING_ONLY" in gate["allowed_decisions"]
