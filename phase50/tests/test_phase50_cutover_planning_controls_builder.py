from phase50.cutover_planning_design.cutover_planning_controls_builder import (
    build_cutover_planning_controls,
)


def test_cutover_planning_controls_have_non_execute_guard() -> None:
    controls = build_cutover_planning_controls({"status": "CUTOVER_PLANNING_PACKAGE_READY"})
    assert controls["status"] == "CUTOVER_PLANNING_CONTROLS_READY"
    assert controls["cutover_planning_controls_does_not_execute"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["single_file_scope_required"] is True
    assert controls["execute_allowed"] is False
