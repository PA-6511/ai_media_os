from phase67.preparation_evidence_design.manual_preparation_gate_builder import (
    build_manual_preparation_gate,
)


def test_manual_gate_allows_phase68_planning_only() -> None:
    gate = build_manual_preparation_gate({"status": "PREPARATION_EVIDENCE_PACKAGE_READY"})
    assert gate["gate_required"] is True
    assert "ALLOW_PHASE68_PLANNING_ONLY" in gate["allowed_decisions"]
    assert gate["manual_preparation_gate_does_not_execute"] is True
