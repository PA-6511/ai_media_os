from phase50.cutover_planning_design.cutover_planning_stop_conditions_builder import (
    build_cutover_planning_stop_conditions,
)


def test_cutover_planning_stop_conditions_are_blocking() -> None:
    data = build_cutover_planning_stop_conditions({"status": "CUTOVER_PLANNING_PACKAGE_READY"})
    assert data["status"] == "CUTOVER_PLANNING_STOP_CONDITIONS_READY"
    assert data["stop_conditions_required"] is True
    assert data["cutover_planning_stop_conditions_does_not_execute"] is True
    assert data["stop_on_sandbox_violation"] is True
