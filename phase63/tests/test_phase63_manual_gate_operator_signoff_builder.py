from phase63.operator_signoff_design.manual_gate_operator_signoff_builder import (
    build_manual_gate_operator_signoff,
)


def test_manual_gate_operator_signoff_allows_phase64_planning_only() -> None:
    gate = build_manual_gate_operator_signoff({"status": "OPERATOR_SIGNOFF_PACKAGE_READY"})
    assert gate["gate_required"] is True
    assert "ALLOW_PHASE64_PLANNING_ONLY" in gate["allowed_decisions"]
    assert gate["operator_signoff_gate_does_not_execute"] is True
