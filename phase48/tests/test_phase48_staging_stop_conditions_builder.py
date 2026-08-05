from phase48.staging_design.staging_stop_conditions_builder import build_staging_stop_conditions


def test_staging_stop_conditions_are_blocking() -> None:
    data = build_staging_stop_conditions({"status": "STAGING_PACKAGE_READY"})
    assert data["status"] == "STAGING_STOP_CONDITIONS_READY"
    assert data["stop_conditions_required"] is True
    assert data["staging_stop_conditions_does_not_execute"] is True
    assert data["stop_on_sandbox_violation"] is True
