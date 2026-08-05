from phase58.execution_plan_design.manual_gate_execution_plan_builder import (
    build_manual_gate_execution_plan,
)


def test_manual_gate_execution_plan_allows_phase59_planning_only() -> None:
    gate = build_manual_gate_execution_plan({"status": "EXECUTION_PLAN_PACKAGE_READY"})
    assert gate["status"] == "MANUAL_GATE_EXECUTION_PLAN_READY"
    assert gate["execution_plan_gate_does_not_execute"] is True
    assert "ALLOW_PHASE59_PLANNING_ONLY" in gate["allowed_decisions"]
