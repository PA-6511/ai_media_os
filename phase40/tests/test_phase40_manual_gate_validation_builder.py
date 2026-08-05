from phase40.validation_design.manual_gate_validation_builder import build_manual_gate_validation


def test_manual_gate_validation_allows_phase41_planning_only() -> None:
    gate = build_manual_gate_validation(
        {"status": "MANUAL_DRY_RUN_EXECUTION_VALIDATION_PACKAGE_READY"}
    )
    assert gate["status"] == "MANUAL_GATE_VALIDATION_READY"
    assert gate["allow_does_not_execute"] is True
    assert "ALLOW_PHASE41_PLANNING_ONLY" in gate["allowed_decisions"]
