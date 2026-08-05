from phase33.approval_design.manual_gate_final_approval_builder import (
    build_manual_gate_final_approval,
)


def test_manual_gate_final_approval_allows_phase34_planning_only() -> None:
    gate = build_manual_gate_final_approval(
        {"status": "MANUAL_DRY_RUN_EXECUTION_APPROVAL_PACKAGE_READY"}
    )
    assert gate["status"] == "MANUAL_GATE_FINAL_APPROVAL_READY"
    assert gate["allow_does_not_execute"] is True
    assert "ALLOW_PHASE34_PLANNING_ONLY" in gate["allowed_decisions"]
