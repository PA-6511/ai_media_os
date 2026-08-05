from phase38.confirmation_design.confirmation_stop_conditions_builder import (
    build_confirmation_stop_conditions,
)


def test_confirmation_stop_conditions_are_blocking_and_non_execute() -> None:
    data = build_confirmation_stop_conditions(
        {"status": "MANUAL_DRY_RUN_EXECUTION_CONFIRMATION_PACKAGE_READY"}
    )
    assert data["status"] == "CONFIRMATION_STOP_CONDITIONS_READY"
    assert data["stop_on_scope_violation"] is True
    assert data["stop_on_sandbox_violation"] is True
    assert data["confirmation_stop_conditions_does_not_execute"] is True
