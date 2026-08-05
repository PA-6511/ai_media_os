from phase32.preflight_design.preflight_stop_conditions_builder import (
    build_preflight_stop_conditions,
)


def test_preflight_stop_conditions_are_blocking_and_non_execute() -> None:
    data = build_preflight_stop_conditions(
        {"status": "MANUAL_DRY_RUN_PREFLIGHT_PACKAGE_READY"}
    )
    assert data["status"] == "PREFLIGHT_STOP_CONDITIONS_READY"
    assert data["stop_on_scope_violation"] is True
    assert data["stop_on_sandbox_violation"] is True
    assert data["preflight_stop_conditions_does_not_execute"] is True
