from phase31.control_design.stop_conditions_builder import build_stop_conditions


def test_stop_conditions_have_non_execute_guard() -> None:
    data = build_stop_conditions({"status": "PRE_EXECUTION_CONTROL_DESIGN_READY"})
    assert data["status"] == "STOP_CONDITIONS_READY"
    assert data["stop_on_scope_violation"] is True
    assert data["stop_on_sandbox_violation"] is True
    assert data["stop_conditions_does_not_execute"] is True
