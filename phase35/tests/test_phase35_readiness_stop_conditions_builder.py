from phase35.readiness_design.readiness_stop_conditions_builder import (
    build_readiness_stop_conditions,
)


def test_readiness_stop_conditions_are_blocking_and_non_execute() -> None:
    data = build_readiness_stop_conditions(
        {"status": "MANUAL_DRY_RUN_EXECUTION_READINESS_PACKAGE_READY"}
    )
    assert data["status"] == "READINESS_STOP_CONDITIONS_READY"
    assert data["stop_on_scope_violation"] is True
    assert data["stop_on_sandbox_violation"] is True
    assert data["readiness_stop_conditions_does_not_execute"] is True
