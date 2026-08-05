from phase50.cutover_planning_design.manual_gate_cutover_planning_builder import (
    build_manual_gate_cutover_planning,
)


def test_manual_gate_cutover_planning_allows_phase51_planning_only() -> None:
    gate = build_manual_gate_cutover_planning({"status": "CUTOVER_PLANNING_PACKAGE_READY"})
    assert gate["status"] == "MANUAL_GATE_CUTOVER_PLANNING_READY"
    assert gate["cutover_planning_gate_does_not_execute"] is True
    assert "ALLOW_PHASE51_PLANNING_ONLY" in gate["allowed_decisions"]
