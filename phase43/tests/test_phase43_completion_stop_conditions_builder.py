from phase43.completion_design.completion_stop_conditions_builder import (
    build_completion_stop_conditions,
)


def test_completion_stop_conditions_are_blocking() -> None:
    data = build_completion_stop_conditions({"status": "COMPLETION_PACKAGE_READY"})
    assert data["status"] == "COMPLETION_STOP_CONDITIONS_READY"
    assert data["stop_conditions_required"] is True
    assert data["stop_on_missing_manual_approval"] is True
    assert data["stop_on_sandbox_violation"] is True
