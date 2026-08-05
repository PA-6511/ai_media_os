from phase60.runbook_design.manual_gate_runbook_builder import (
    build_manual_gate_runbook,
)


def test_manual_gate_runbook_allows_phase61_planning_only() -> None:
    gate = build_manual_gate_runbook({"status": "RUNBOOK_PACKAGE_READY"})
    assert gate["status"] == "MANUAL_GATE_RUNBOOK_READY"
    assert gate["runbook_gate_does_not_execute"] is True
    assert "ALLOW_PHASE61_PLANNING_ONLY" in gate["allowed_decisions"]
