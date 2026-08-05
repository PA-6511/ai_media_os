from phase49.release_planning_design.manual_gate_release_planning_builder import (
    build_manual_gate_release_planning,
)


def test_manual_gate_release_planning_allows_phase50_planning_only() -> None:
    gate = build_manual_gate_release_planning({"status": "RELEASE_PLANNING_PACKAGE_READY"})
    assert gate["status"] == "MANUAL_GATE_RELEASE_PLANNING_READY"
    assert gate["release_planning_gate_does_not_execute"] is True
    assert "ALLOW_PHASE50_PLANNING_ONLY" in gate["allowed_decisions"]
