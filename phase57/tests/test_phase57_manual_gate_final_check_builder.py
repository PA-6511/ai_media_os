from phase57.final_check_design.manual_gate_final_check_builder import (
    build_manual_gate_final_check,
)


def test_manual_gate_final_check_allows_phase58_planning_only() -> None:
    gate = build_manual_gate_final_check({"status": "FINAL_CHECK_PACKAGE_READY"})
    assert gate["status"] == "MANUAL_GATE_FINAL_CHECK_READY"
    assert gate["final_check_gate_does_not_execute"] is True
    assert "ALLOW_PHASE58_PLANNING_ONLY" in gate["allowed_decisions"]
