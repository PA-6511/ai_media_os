from phase44.closure_design.closure_stop_conditions_builder import build_closure_stop_conditions


def test_closure_stop_conditions_are_blocking() -> None:
    data = build_closure_stop_conditions({"status": "CLOSURE_PACKAGE_READY"})
    assert data["status"] == "CLOSURE_STOP_CONDITIONS_READY"
    assert data["stop_conditions_required"] is True
    assert data["closure_stop_conditions_does_not_execute"] is True
    assert data["stop_on_sandbox_violation"] is True
