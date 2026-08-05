from phase45.handoff_design.handoff_stop_conditions_builder import build_handoff_stop_conditions


def test_handoff_stop_conditions_are_blocking() -> None:
    data = build_handoff_stop_conditions({"status": "HANDOFF_PACKAGE_READY"})
    assert data["status"] == "HANDOFF_STOP_CONDITIONS_READY"
    assert data["stop_conditions_required"] is True
    assert data["handoff_stop_conditions_does_not_execute"] is True
    assert data["stop_on_sandbox_violation"] is True
