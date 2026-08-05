from phase42.finalization_design.manual_gate_finalization_builder import build_manual_gate_finalization


def test_manual_gate_finalization_allows_phase43_planning_only() -> None:
    gate = build_manual_gate_finalization(
        {"status": "MANUAL_DRY_RUN_EXECUTION_FINALIZATION_PACKAGE_READY"}
    )
    assert gate["status"] == "MANUAL_GATE_FINALIZATION_READY"
    assert gate["allow_does_not_execute"] is True
    assert "ALLOW_PHASE43_PLANNING_ONLY" in gate["allowed_decisions"]
