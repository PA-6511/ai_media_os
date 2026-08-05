from phase42.finalization_design.finalization_stop_conditions_builder import (
    build_finalization_stop_conditions,
)


def test_finalization_stop_conditions_are_blocking_and_non_execute() -> None:
    data = build_finalization_stop_conditions(
        {"status": "MANUAL_DRY_RUN_EXECUTION_FINALIZATION_PACKAGE_READY"}
    )
    assert data["status"] == "FINALIZATION_STOP_CONDITIONS_READY"
    assert data["stop_on_scope_violation"] is True
    assert data["stop_on_sandbox_violation"] is True
    assert data["finalization_stop_conditions_does_not_execute"] is True
