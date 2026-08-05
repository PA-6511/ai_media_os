from phase57.final_check_design.final_check_stop_conditions_builder import (
    build_final_check_stop_conditions,
)


def test_final_check_stop_conditions_are_blocking() -> None:
    data = build_final_check_stop_conditions({"status": "FINAL_CHECK_PACKAGE_READY"})
    assert data["status"] == "FINAL_CHECK_STOP_CONDITIONS_READY"
    assert data["stop_conditions_required"] is True
    assert data["final_check_stop_conditions_does_not_execute"] is True
    assert data["stop_on_sandbox_violation"] is True
