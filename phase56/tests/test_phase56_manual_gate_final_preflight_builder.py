from phase56.final_preflight_design.manual_gate_final_preflight_builder import (
    build_manual_gate_final_preflight,
)


def test_manual_gate_final_preflight_allows_phase57_planning_only() -> None:
    gate = build_manual_gate_final_preflight({"status": "FINAL_PREFLIGHT_PACKAGE_READY"})
    assert gate["status"] == "MANUAL_GATE_FINAL_PREFLIGHT_READY"
    assert gate["final_preflight_gate_does_not_execute"] is True
    assert "ALLOW_PHASE57_PLANNING_ONLY" in gate["allowed_decisions"]
