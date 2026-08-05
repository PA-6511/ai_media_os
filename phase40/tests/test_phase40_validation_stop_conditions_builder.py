from phase40.validation_design.validation_stop_conditions_builder import (
    build_validation_stop_conditions,
)


def test_validation_stop_conditions_are_blocking_and_non_execute() -> None:
    data = build_validation_stop_conditions(
        {"status": "MANUAL_DRY_RUN_EXECUTION_VALIDATION_PACKAGE_READY"}
    )
    assert data["status"] == "VALIDATION_STOP_CONDITIONS_READY"
    assert data["stop_on_scope_violation"] is True
    assert data["stop_on_sandbox_violation"] is True
    assert data["validation_stop_conditions_does_not_execute"] is True
