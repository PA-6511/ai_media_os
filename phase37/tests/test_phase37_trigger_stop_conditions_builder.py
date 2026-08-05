from phase37.trigger_design.trigger_stop_conditions_builder import build_trigger_stop_conditions


def test_trigger_stop_conditions_are_blocking_and_non_execute() -> None:
    data = build_trigger_stop_conditions(
        {"status": "MANUAL_DRY_RUN_EXECUTION_TRIGGER_PACKAGE_READY"}
    )
    assert data["status"] == "TRIGGER_STOP_CONDITIONS_READY"
    assert data["stop_on_scope_violation"] is True
    assert data["stop_on_sandbox_violation"] is True
    assert data["trigger_stop_conditions_does_not_execute"] is True
