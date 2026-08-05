from phase54.final_authorization_design.manual_gate_final_authorization_builder import (
    build_manual_gate_final_authorization,
)


def test_manual_gate_final_authorization_allows_phase55_planning_only() -> None:
    gate = build_manual_gate_final_authorization({"status": "FINAL_AUTHORIZATION_PACKAGE_READY"})
    assert gate["status"] == "MANUAL_GATE_FINAL_AUTHORIZATION_READY"
    assert gate["final_authorization_gate_does_not_execute"] is True
    assert "ALLOW_PHASE55_PLANNING_ONLY" in gate["allowed_decisions"]
