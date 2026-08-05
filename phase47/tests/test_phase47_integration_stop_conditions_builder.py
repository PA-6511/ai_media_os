from phase47.integration_design.integration_stop_conditions_builder import (
    build_integration_stop_conditions,
)


def test_integration_stop_conditions_are_blocking() -> None:
    data = build_integration_stop_conditions({"status": "INTEGRATION_PACKAGE_READY"})
    assert data["status"] == "INTEGRATION_STOP_CONDITIONS_READY"
    assert data["stop_conditions_required"] is True
    assert data["integration_stop_conditions_does_not_execute"] is True
    assert data["stop_on_sandbox_violation"] is True
