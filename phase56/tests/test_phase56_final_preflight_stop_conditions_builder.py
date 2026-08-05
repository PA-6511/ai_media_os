from phase56.final_preflight_design.final_preflight_stop_conditions_builder import (
    build_final_preflight_stop_conditions,
)


def test_final_preflight_stop_conditions_are_blocking() -> None:
    data = build_final_preflight_stop_conditions({"status": "FINAL_PREFLIGHT_PACKAGE_READY"})
    assert data["status"] == "FINAL_PREFLIGHT_STOP_CONDITIONS_READY"
    assert data["stop_conditions_required"] is True
    assert data["final_preflight_stop_conditions_does_not_execute"] is True
    assert data["stop_on_sandbox_violation"] is True
