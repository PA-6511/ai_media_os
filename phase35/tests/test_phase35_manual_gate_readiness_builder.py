from phase35.readiness_design.manual_gate_readiness_builder import (
    build_manual_gate_readiness,
)


def test_manual_gate_readiness_allows_phase36_planning_only() -> None:
    gate = build_manual_gate_readiness(
        {"status": "MANUAL_DRY_RUN_EXECUTION_READINESS_PACKAGE_READY"}
    )
    assert gate["status"] == "MANUAL_GATE_READINESS_READY"
    assert gate["allow_does_not_execute"] is True
    assert "ALLOW_PHASE36_PLANNING_ONLY" in gate["allowed_decisions"]
