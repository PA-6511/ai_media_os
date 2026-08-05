from phase55.final_readiness_design.manual_gate_final_readiness_builder import (
    build_manual_gate_final_readiness,
)


def test_manual_gate_final_readiness_allows_phase56_planning_only() -> None:
    gate = build_manual_gate_final_readiness({"status": "FINAL_READINESS_PACKAGE_READY"})
    assert gate["status"] == "MANUAL_GATE_FINAL_READINESS_READY"
    assert gate["final_readiness_gate_does_not_execute"] is True
    assert "ALLOW_PHASE56_PLANNING_ONLY" in gate["allowed_decisions"]
