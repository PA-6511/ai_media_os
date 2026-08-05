from phase46.transition_design.transition_stop_conditions_builder import (
    build_transition_stop_conditions,
)


def test_transition_stop_conditions_are_blocking() -> None:
    data = build_transition_stop_conditions({"status": "TRANSITION_PACKAGE_READY"})
    assert data["status"] == "TRANSITION_STOP_CONDITIONS_READY"
    assert data["stop_conditions_required"] is True
    assert data["transition_stop_conditions_does_not_execute"] is True
    assert data["stop_on_sandbox_violation"] is True
