from phase32.preflight_design.manual_gate_preflight_builder import (
    build_manual_gate_preflight,
)


def test_manual_gate_preflight_allows_phase33_planning_only() -> None:
    gate = build_manual_gate_preflight(
        {"status": "MANUAL_DRY_RUN_PREFLIGHT_PACKAGE_READY"}
    )
    assert gate["status"] == "MANUAL_GATE_PREFLIGHT_READY"
    assert gate["allow_does_not_execute"] is True
    assert "ALLOW_PHASE33_PLANNING_ONLY" in gate["allowed_decisions"]
