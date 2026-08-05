from phase37.trigger_design.manual_gate_trigger_builder import build_manual_gate_trigger


def test_manual_gate_trigger_allows_phase38_planning_only() -> None:
    gate = build_manual_gate_trigger(
        {"status": "MANUAL_DRY_RUN_EXECUTION_TRIGGER_PACKAGE_READY"}
    )
    assert gate["status"] == "MANUAL_GATE_TRIGGER_READY"
    assert gate["allow_does_not_execute"] is True
    assert "ALLOW_PHASE38_PLANNING_ONLY" in gate["allowed_decisions"]
