from phase31.control_design.manual_gate_final_check_builder import (
    build_manual_gate_final_check,
)


def test_manual_gate_final_check_allows_phase32_planning_only() -> None:
    gate = build_manual_gate_final_check(
        {"status": "PRE_EXECUTION_CONTROL_DESIGN_READY"}
    )
    assert gate["status"] == "MANUAL_GATE_FINAL_CHECK_READY"
    assert gate["allow_does_not_execute"] is True
    assert "ALLOW_PHASE32_PLANNING_ONLY" in gate["allowed_decisions"]
