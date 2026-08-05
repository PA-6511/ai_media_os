from phase61.operator_checklist_design.manual_gate_operator_checklist_builder import (
    build_manual_gate_operator_checklist,
)


def test_manual_gate_operator_checklist_allows_phase62_planning_only() -> None:
    gate = build_manual_gate_operator_checklist({"status": "OPERATOR_CHECKLIST_PACKAGE_READY"})
    assert gate["gate_required"] is True
    assert "ALLOW_PHASE62_PLANNING_ONLY" in gate["allowed_decisions"]
    assert gate["operator_checklist_gate_does_not_execute"] is True
