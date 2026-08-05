from phase49.release_planning_design.release_planning_stop_conditions_builder import (
    build_release_planning_stop_conditions,
)


def test_release_planning_stop_conditions_are_blocking() -> None:
    data = build_release_planning_stop_conditions({"status": "RELEASE_PLANNING_PACKAGE_READY"})
    assert data["status"] == "RELEASE_PLANNING_STOP_CONDITIONS_READY"
    assert data["stop_conditions_required"] is True
    assert data["release_planning_stop_conditions_does_not_execute"] is True
    assert data["stop_on_sandbox_violation"] is True
