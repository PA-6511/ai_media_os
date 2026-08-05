from phase38.confirmation_design.manual_gate_confirmation_builder import (
    build_manual_gate_confirmation,
)


def test_manual_gate_confirmation_allows_phase39_planning_only() -> None:
    gate = build_manual_gate_confirmation(
        {"status": "MANUAL_DRY_RUN_EXECUTION_CONFIRMATION_PACKAGE_READY"}
    )
    assert gate["status"] == "MANUAL_GATE_CONFIRMATION_READY"
    assert gate["allow_does_not_execute"] is True
    assert "ALLOW_PHASE39_PLANNING_ONLY" in gate["allowed_decisions"]
