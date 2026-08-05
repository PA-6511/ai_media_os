from phase49.release_planning_design.release_planning_controls_builder import (
    build_release_planning_controls,
)


def test_release_planning_controls_have_non_execute_guard() -> None:
    controls = build_release_planning_controls({"status": "RELEASE_PLANNING_PACKAGE_READY"})
    assert controls["status"] == "RELEASE_PLANNING_CONTROLS_READY"
    assert controls["release_planning_controls_does_not_execute"] is True
    assert controls["sandbox_scope_required"] is True
    assert controls["single_file_scope_required"] is True
    assert controls["execute_allowed"] is False
