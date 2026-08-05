from phase59.operation_plan_design.manual_gate_operation_plan_builder import (
    build_manual_gate_operation_plan,
)


def test_manual_gate_operation_plan_allows_phase60_planning_only() -> None:
    gate = build_manual_gate_operation_plan({"status": "OPERATION_PLAN_PACKAGE_READY"})
    assert gate["status"] == "MANUAL_GATE_OPERATION_PLAN_READY"
    assert gate["operation_plan_gate_does_not_execute"] is True
    assert "ALLOW_PHASE60_PLANNING_ONLY" in gate["allowed_decisions"]
