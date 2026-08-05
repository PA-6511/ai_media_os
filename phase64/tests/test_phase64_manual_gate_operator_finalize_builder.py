from phase64.operator_finalize_design.manual_gate_operator_finalize_builder import (
    build_manual_gate_operator_finalize,
)


def test_manual_gate_operator_finalize_allows_phase65_planning_only() -> None:
    gate = build_manual_gate_operator_finalize({"status": "OPERATOR_FINALIZE_PACKAGE_READY"})
    assert gate["gate_required"] is True
    assert "ALLOW_PHASE65_PLANNING_ONLY" in gate["allowed_decisions"]
    assert gate["operator_finalize_gate_does_not_execute"] is True
