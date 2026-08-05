from phase39.authorization_design.manual_gate_authorization_builder import (
    build_manual_gate_authorization,
)


def test_manual_gate_authorization_allows_phase40_planning_only() -> None:
    gate = build_manual_gate_authorization(
        {"status": "MANUAL_DRY_RUN_EXECUTION_AUTHORIZATION_PACKAGE_READY"}
    )
    assert gate["status"] == "MANUAL_GATE_AUTHORIZATION_READY"
    assert gate["allow_does_not_execute"] is True
    assert "ALLOW_PHASE40_PLANNING_ONLY" in gate["allowed_decisions"]
