from phase62.operator_approval_design.manual_gate_operator_approval_builder import (
    build_manual_gate_operator_approval,
)


def test_manual_gate_operator_approval_allows_phase63_planning_only() -> None:
    gate = build_manual_gate_operator_approval({"status": "OPERATOR_APPROVAL_PACKAGE_READY"})
    assert gate["gate_required"] is True
    assert "ALLOW_PHASE63_PLANNING_ONLY" in gate["allowed_decisions"]
    assert gate["operator_approval_gate_does_not_execute"] is True
